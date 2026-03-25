import pytest
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
