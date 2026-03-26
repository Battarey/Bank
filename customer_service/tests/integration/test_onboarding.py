import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from shared.models import User, PersonalData, Contact

@pytest.mark.asyncio
async def test_onboarding_happy_path(client: AsyncClient, db_session: AsyncSession):
	"""Полный цикл онбординга: от создания пользователя до финализации (успешный путь)."""
	
	# 1. Начало онбординга
	response = await client.post("/users/start")
	assert response.status_code == 201
	user_id = response.json()["user_id"]
	user_uuid = uuid.UUID(user_id)
	
	# 2. Персональные данные
	payload_pd = {
		"first_name": "Иван",
		"last_name": "Иванов",
		"middle_name": "Иванович",
		"birth_date": "1990-01-01",
		"gender": "M"
	}
	response = await client.post(f"/users/{user_id}/account/personal-data", json=payload_pd)
	assert response.status_code == 201
	
	# 3. Паспортные данные
	payload_pass = {
		"series": "1234",
		"number": "567890",
		"division_code": "123-456",
		"issued_by": "УВД города Москвы",
		"issued_at": "2010-01-01",
		"expiration_date": "2030-01-01",
		"registration_address": "г. Москва, ул. Ленина, д. 1"
	}
	response = await client.post(f"/users/{user_id}/account/passport", json=payload_pass)
	assert response.status_code == 201
	
	# 4. Идентификаторы
	payload_ids = {
		"inn": "123456789012",
		"snils": "12345678901"
	}
	response = await client.post(f"/users/{user_id}/account/identifiers", json=payload_ids)
	assert response.status_code == 201
	
	# 5. Контакты
	payload_contacts = {
		"email": "test@example.com",
		"phone": "+79991234567"
	}
	response = await client.post(f"/users/{user_id}/account/contacts", json=payload_contacts)
	assert response.status_code == 201
	
	# 6. Отправка кода подтверждения
	response = await client.post(f"/users/{user_id}/account/send-email-code")
	assert response.status_code == 200
	
	# Получаем код напрямую из Redis для теста
	from shared.redis_onboarding.client import get_client
	client_redis = get_client()
	code_key = f"onboarding:{user_id}:email_code"
	code = await client_redis.get(code_key)
	assert code is not None
	
	# 7. Подтверждение email
	response = await client.post(f"/users/{user_id}/account/verify-email", json={"code": code})
	assert response.status_code == 200
	assert response.json()["email_verified"] is True
	
	# 8. Финализация
	response = await client.post(f"/users/{user_id}/account/finalize")
	assert response.status_code == 200
	assert response.json()["status"] == "completed"
	
	# Проверка, что данные попали в БД
	db_session.expire_all()
	user = await db_session.get(User, user_uuid)
	
	assert user is not None
	assert user.status == "active"
	assert user.is_verified is True


@pytest.mark.asyncio
async def test_onboarding_validation_errors(client: AsyncClient):
	"""Тестирование ошибок валидации на разных этапах онбординга."""
	
	# Начинаем онбординг
	response = await client.post("/users/start")
	user_id = response.json()["user_id"]

	# Ошибка в паспорте (срок действия раньше даты выдачи)
	payload_pass = {
		"series": "1234",
		"number": "567890",
		"division_code": "123-456",
		"issued_by": "УВД города Москвы",
		"issued_at": "2020-01-01",
		"expiration_date": "2010-01-01",
		"registration_address": "г. Москва"
	}
	response = await client.post(f"/users/{user_id}/account/passport", json=payload_pass)
	assert response.status_code == 422
	assert "expiration_date must be later than issued_at" in response.text

	# Ошибка в идентификаторах (ИНН не 12 цифр)
	payload_ids = {
		"inn": "123", # Мало цифр
		"snils": "12345678901"
	}
	response = await client.post(f"/users/{user_id}/account/identifiers", json=payload_ids)
	assert response.status_code == 422

	# Ошибка в контактах (неверный формат email)
	payload_contacts = {
		"email": "invalid-email",
		"phone": "+79991234567"
	}
	response = await client.post(f"/users/{user_id}/account/contacts", json=payload_contacts)
	# В Pydantic EmailStr может не быть подключен, проверим что вернет 422 если есть валидация
	# Если валидации нет в схеме, то тест упадет, что тоже полезно для выявления недостатков.
	assert response.status_code == 422


@pytest.mark.asyncio
async def test_onboarding_state_machine_violations(client: AsyncClient):
	"""Тестирование нарушения последовательности шагов онбординга."""
	
	# Начинаем онбординг
	response = await client.post("/users/start")
	user_id = response.json()["user_id"]

	# Попытка финализации без данных
	response = await client.post(f"/users/{user_id}/account/finalize")
	assert response.status_code == 400
	assert "Не заполнены или истекли черновики шагов" in response.text

	# Попытка отправить код без заполнения контактов
	response = await client.post(f"/users/{user_id}/account/send-email-code")
	assert response.status_code == 400
	assert "Сначала заполните контактные данные" in response.text

	# Попытка верификации с неправильным кодом
	response = await client.post(f"/users/{user_id}/account/verify-email", json={"code": "000000"})
	assert response.status_code == 400
	assert "Код неверный или истёк" in response.text


@pytest.mark.asyncio
async def test_onboarding_duplicate_data(client: AsyncClient):
	"""Тестирование конфликтов при использовании дублирующихся данных."""
	
	# 1. Регистрируем первого пользователя успешно
	res1 = await client.post("/users/start")
	u1 = res1.json()["user_id"]
	
	# Заполняем минимальный набор для финализации
	await client.post(f"/users/{u1}/account/personal-data", json={
		"first_name": "ИВАН", "last_name": "ИВАНОВ", "middle_name": "ИВАНОВИЧ",
		"birth_date": "1990-01-01", "gender": "M"
	})
	await client.post(f"/users/{u1}/account/passport", json={
		"series": "1111", "number": "111111", "division_code": "111-111",
		"issued_by": "УВД", "issued_at": "2010-01-01", "expiration_date": "2030-01-01",
		"registration_address": "г. Москва"
	})
	await client.post(f"/users/{u1}/account/identifiers", json={"inn": "123456789012", "snils": "11122233344"})
	await client.post(f"/users/{u1}/account/contacts", json={"email": "u1@example.com", "phone": "+79991112233"})
	
	# Верифицируем (получаем код из Redis)
	from shared.redis_onboarding.client import get_client
	client_redis = get_client()
	await client.post(f"/users/{u1}/account/send-email-code")
	code = await client_redis.get(f"onboarding:{u1}:email_code")
	await client.post(f"/users/{u1}/account/verify-email", json={"code": code})
	
	# Финализируем
	await client.post(f"/users/{u1}/account/finalize")
	
	# 2. Пытаемся зарегистрировать второго пользователя с ТЕМИ ЖЕ данными
	res2 = await client.post("/users/start")
	u2 = res2.json()["user_id"]
	
	# Конфликт по ИНН
	response = await client.post(f"/users/{u2}/account/identifiers", json={"inn": "123456789012", "snils": "22233344455"})
	assert response.status_code == 409
	assert "INN or SNILS already belongs to another client" in response.text

	# Конфликт по Email
	response = await client.post(f"/users/{u2}/account/contacts", json={"email": "u1@example.com", "phone": "+79998887766"})
	assert response.status_code == 409
	assert "email or phone already belongs to another client" in response.text.lower()

