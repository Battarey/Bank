import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from shared.models import User, PersonalData, Contact

@pytest.mark.asyncio
async def test_full_onboarding_flow(client: AsyncClient, db_session: AsyncSession):
	"""Полный цикл онбординга: от создания пользователя до финализации."""
	
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
	
	# Нужно сбросить кэш сессии, expire_all() не awaitable в asyncpg, поэтому:
	db_session.expire_all()
	user = await db_session.get(User, user_uuid)
	
	assert user is not None
	assert user.status == "active"
	assert user.is_verified is True
	
	pd = await db_session.get(PersonalData, user_uuid)
	assert pd is not None
	assert pd.first_name == "ИВАН"
	assert pd.last_name == "ИВАНОВ"
	assert pd.middle_name == "ИВАНОВИЧ"
	
	contact = await db_session.get(Contact, user_uuid)
	assert contact is not None
	assert contact.email == "test@example.com"
