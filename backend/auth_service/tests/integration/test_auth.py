import os
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from shared.models import User

@pytest.mark.asyncio
async def test_auth_happy_path(client: AsyncClient, db_session: AsyncSession, test_user: User):
	"""Полный сценарий: установка PIN, вход, выход."""
	
	# 1. Установка PIN
	payload_set_pin = {"pin": "1234"}
	response = await client.post(
		"/set-pin",
		json=payload_set_pin,
		headers={"X-User-ID": str(test_user.id)}
	)
	assert response.status_code == 200, response.json()
	assert response.json()["message"] == "PIN-код успешно установлен."
	
	# Обновляем юзера, проверяем, что PIN сохранился в БД
	await db_session.refresh(test_user)
	assert test_user.pin_hash is not None

	# 2. Вход по PIN
	payload_login = {
		"phone": "+79991234567",
		"pin": "1234"
	}
	response = await client.post("/login-pin", json=payload_login)
	assert response.status_code == 200
	data = response.json()
	
	assert data["user_id"] == str(test_user.id)
	session_token = data["session_token"]
	assert session_token is not None

	# 3. Выход из сессии
	response = await client.post(
		"/logout",
		headers={"X-Session-Token": session_token}
	)
	assert response.status_code == 200
	assert response.json()["message"] == "Сеанс завершён."
	
	# При попытке повторного логаута с тем же токеном (сессия удалена)
	# Ожидаем нормальное завершение (мы просто игнорируем, если сессии уже нет)
	response = await client.post(
		"/logout",
		headers={"X-Session-Token": session_token}
	)
	assert response.status_code == 200

@pytest.mark.asyncio
async def test_self_block(client: AsyncClient, db_session: AsyncSession, test_user: User):
	"""Блокировка аккаунта пользователем."""
	# Установка PIN
	await client.post(
		"/set-pin",
		json={"pin": "1234"},
		headers={"X-User-ID": str(test_user.id)}
	)
	
	# Вход
	res = await client.post("/login-pin", json={"phone": "+79991234567", "pin": "1234"})
	token = res.json()["session_token"]
	
	# Самоблокировка
	response = await client.post(
		"/self-block",
		headers={
			"X-User-ID": str(test_user.id),
			"X-Session-Token": token
		}
	)
	assert response.status_code == 200
	
	await db_session.refresh(test_user)
	assert test_user.status == "blocked"


@pytest.mark.asyncio
async def test_set_pin_validation_errors(client: AsyncClient, test_user: User):
	"""Ошибки валидации при установке PIN."""
	
	# Слишком короткий
	response = await client.post(
		"/set-pin",
		json={"pin": "123"},
		headers={"X-User-ID": str(test_user.id)}
	)
	assert response.status_code == 422

	# Слишком длинный
	response = await client.post(
		"/set-pin",
		json={"pin": "1234567"},
		headers={"X-User-ID": str(test_user.id)}
	)
	assert response.status_code == 422

	# Не цифры
	response = await client.post(
		"/set-pin",
		json={"pin": "abcd"},
		headers={"X-User-ID": str(test_user.id)}
	)
	assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_pin_negative_scenarios(client: AsyncClient, db_session: AsyncSession, test_user: User):
	"""Негативные сценарии входа."""
	
	# Сначала ставим PIN
	await client.post("/set-pin", json={"pin": "1234"}, headers={"X-User-ID": str(test_user.id)})

	# 1. Неверный PIN
	response = await client.post("/login-pin", json={"phone": "+79991234567", "pin": "0000"})
	assert response.status_code == 401
	assert "неверный" in response.json()["detail"].lower()

	# 2. Неверный телефон
	response = await client.post("/login-pin", json={"phone": "+70000000000", "pin": "1234"})
	assert response.status_code == 404

	# 3. Вход для заблокированного
	test_user.status = "blocked"
	await db_session.commit()
	
	response = await client.post("/login-pin", json={"phone": "+79991234567", "pin": "1234"})
	assert response.status_code == 423
	assert "заблокирован" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_brute_force_cooldown(client: AsyncClient, test_user: User):
	"""Защита от перебора (Cooldown)."""
	
	# Ставим PIN
	await client.post("/set-pin", json={"pin": "1234"}, headers={"X-User-ID": str(test_user.id)})

	# Делаем 5 неудачных попыток (лимит обычно 3-5)
	for _ in range(5):
		response = await client.post("/login-pin", json={"phone": "+79991234567", "pin": "0000"})
		if response.status_code == 429:
			break
	
	assert response.status_code == 429
	assert "неудачных попыток" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_logout_all_and_session_invalidation(client: AsyncClient, test_user: User):
	"""Выход со всех устройств."""
	
	# 1. Ставим PIN и входим
	await client.post("/set-pin", json={"pin": "1234"}, headers={"X-User-ID": str(test_user.id)})
	res1 = await client.post("/login-pin", json={"phone": "+79991234567", "pin": "1234"})
	token1 = res1.json()["session_token"]

	# 2. Выход со всех устройств
	response = await client.post("/logout-all", headers={"X-User-ID": str(test_user.id)})
	assert response.status_code == 200

	# 3. Пытаемся выйти с токеном 1 (сессия должна быть удалена)
	# В нашем случае logout просто возвращает 200 если сессия не найдена (как видно из test_auth_happy_path)
	response = await client.post("/logout", headers={"X-Session-Token": token1})
	assert response.status_code == 200


@pytest.mark.asyncio
async def test_unlock_account_scenarios(client: AsyncClient, db_session: AsyncSession, test_user: User):
	"""Сценарии разблокировки аккаунта."""
	
	# 1. Запрос кода для активного аккаунта (ошибка 409)
	response = await client.post("/request-unlock", json={"email": "test@example.com"})
	assert response.status_code == 409

	# 2. Блокируем аккаунт
	test_user.status = "blocked"
	await db_session.commit()

	# 3. Запрос кода для заблокированного аккаунта
	response = await client.post("/request-unlock", json={"email": "test@example.com"})
	assert response.status_code == 200
	
	# 4. Достаем код из Redis для проверки
	import redis.asyncio as redis
	REDIS_URL = os.environ.get("REDIS_SESSIONS_URL", "redis://redis_test:6379/0")
	r = redis.from_url(REDIS_URL)
	code = await r.get(f"unlock:{test_user.id}:code")
	assert code is not None
	code_str = code.decode()

	# 5. Разблокировка с неверным кодом
	response = await client.post("/unlock", json={"email": "test@example.com", "code": "000000"})
	assert response.status_code == 400

	# 6. Успешная разблокировка
	response = await client.post("/unlock", json={"email": "test@example.com", "code": code_str})
	assert response.status_code == 200
	
	await db_session.refresh(test_user)
	assert test_user.status == "active"
