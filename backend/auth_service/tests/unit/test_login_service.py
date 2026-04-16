from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from auth_service.core.exceptions import (
	AuthCooldown,
	AuthForbidden,
	AuthNotFound,
)
from auth_service.services.login import login_pin, login_quick, set_pin
from shared import models

# --- Тесты login_pin ---


@pytest.fixture
def user_data():
	"""Фикстура для тестовых данных пользователя."""
	user = models.User(
		id=uuid4(),
		status="active",
		pin_hash="$2b$12$LQv3c1yqBWVHxkd0LNJ3eeQEdXQy8H.NIsS00305sU1Yh2z.oZ7C.",  # хеш "1234"
	)
	contact = models.Contact(client_id=user.id, email="test@test.com", phone="+79991234567")
	return user, contact


@pytest.mark.asyncio
@patch("auth_service.services.login.rate_limit")
async def test_login_pin_cooldown(mock_rate_limit, uow):
	"""Проверка ошибки, если превышен лимит попыток (cooldown)."""
	mock_rate_limit.check = AsyncMock(return_value=(True, 60, 5))

	with pytest.raises(AuthCooldown) as exc:
		await login_pin(uow, "+79991234567", "1234")

	assert exc.value.details["retry_after_seconds"] == 60


@pytest.mark.asyncio
@patch("auth_service.services.login.rate_limit")
@patch("auth_service.services.login.get_blind_index")
async def test_login_pin_user_not_found(mock_blind, mock_rate_limit, uow):  # noqa: ARG001
	"""Проверка ошибки, если пользователь не найден."""
	mock_rate_limit.check = AsyncMock(return_value=(False, 0, 0))
	uow.users.get_by_phone.return_value = None

	with pytest.raises(AuthNotFound):
		await login_pin(uow, "+79991234567", "1234")


@pytest.mark.asyncio
@patch("auth_service.services.login.rate_limit")
@patch("auth_service.services.login.get_blind_index")
async def test_login_pin_blocked(mock_blind, mock_rate_limit, uow, user_data):  # noqa: ARG001
	"""Проверка ошибки, если аккаунт заблокирован."""
	user, contact = user_data
	user.status = "blocked"
	mock_rate_limit.check = AsyncMock(return_value=(False, 0, 0))
	uow.users.get_by_phone.return_value = (user, contact)

	with pytest.raises(AuthForbidden, match="заблокирован"):
		await login_pin(uow, "+79991234567", "1234")


@pytest.mark.asyncio
@patch("auth_service.services.login.rate_limit")
@patch("auth_service.services.login.get_blind_index")
async def test_login_pin_wrong_pin(mock_blind, mock_rate_limit, uow, user_data):  # noqa: ARG001
	"""Проверка ошибки при неверном PIN-коде и регистрации события."""
	user, contact = user_data
	mock_rate_limit.check = AsyncMock(return_value=(False, 0, 4))  # 4 предыдущих неудачи
	uow.users.get_by_phone.return_value = (user, contact)
	mock_rate_limit.increment = AsyncMock()
	mock_rate_limit.reset = AsyncMock()

	with pytest.raises(AuthForbidden, match="Неверный PIN-код"):
		await login_pin(uow, "+79991234567", "0000")

	mock_rate_limit.increment.assert_awaited_once_with("+79991234567")
	# Проверка регистрации события (5-я попытка)
	assert any(e.action == "login_failure" for e in uow.events)


@pytest.mark.asyncio
@patch("auth_service.services.login.session_tokens")
@patch("auth_service.services.login.rate_limit")
@patch("auth_service.services.login.get_blind_index")
@patch("auth_service.services.login.bcrypt")
async def test_login_pin_success(mock_bcrypt, mock_blind, mock_rate_limit, mock_tokens, uow, user_data):  # noqa: ARG001
	"""Успешный вход с генерацией токена и событием."""
	user, contact = user_data
	mock_rate_limit.check = AsyncMock(return_value=(False, 0, 0))
	mock_rate_limit.reset = AsyncMock()
	uow.users.get_by_phone.return_value = (user, contact)
	mock_tokens.create_token = AsyncMock(return_value="fake_session")
	mock_tokens.create_refresh_token = AsyncMock(return_value="fake_refresh")
	mock_bcrypt.checkpw.return_value = True

	session, refresh, u_id = await login_pin(uow, "+79991234567", "1234")

	assert session == "fake_session"
	assert refresh == "fake_refresh"
	assert u_id == user.id
	assert uow.committed is True
	mock_rate_limit.reset.assert_awaited_once_with("+79991234567")
	assert any(e.action == "login" and e.status == "success" for e in uow.events)


@pytest.mark.asyncio
@patch("auth_service.services.login.session_tokens")
@patch("auth_service.services.login.bcrypt")
async def test_login_quick_success(mock_bcrypt, mock_tokens, uow, user_data):
	"""Успешный быстрый вход с ротацией токенов."""
	user, contact = user_data
	mock_tokens.load_refresh_token = AsyncMock(return_value=user.id)
	uow.users.get_user_with_contact.return_value = (user, contact)
	mock_bcrypt.checkpw.return_value = True
	mock_tokens.delete_refresh_token = AsyncMock()
	mock_tokens.create_token = AsyncMock(return_value="new_session")
	mock_tokens.create_refresh_token = AsyncMock(return_value="new_refresh")

	s, r, u_id = await login_quick(uow, "old_refresh", "1234")

	assert s == "new_session"
	assert r == "new_refresh"
	assert u_id == user.id
	mock_tokens.delete_refresh_token.assert_awaited_once_with("old_refresh")
	assert uow.committed is True
	assert any(e.action == "quick_login" for e in uow.events)


@pytest.mark.asyncio
@patch("auth_service.services.login.session_tokens")
async def test_login_quick_invalid_token(mock_tokens, uow):
	"""Ошибка быстрого входа при невалидном токене."""
	mock_tokens.load_refresh_token = AsyncMock(return_value=None)

	with pytest.raises(AuthForbidden, match="недействителен или истек"):
		await login_quick(uow, "invalid_token", "1234")


@pytest.mark.asyncio
@patch("auth_service.services.login.session_tokens")
@patch("auth_service.services.login.rate_limit")
@patch("auth_service.services.login.bcrypt")
async def test_login_quick_wrong_pin(mock_bcrypt, mock_rate_limit, mock_tokens, uow, user_data):
	"""Ошибка быстрого входа при неверном PIN (с инкрементацией лимитов)."""
	user, contact = user_data
	mock_tokens.load_refresh_token = AsyncMock(return_value=user.id)
	uow.users.get_user_with_contact.return_value = (user, contact)
	mock_bcrypt.checkpw.return_value = False
	mock_rate_limit.increment = AsyncMock()

	with pytest.raises(AuthForbidden, match="Неверный PIN-код"):
		await login_quick(uow, "valid_refresh", "0000")

	mock_rate_limit.increment.assert_awaited_once_with(contact.phone)


# --- Тесты set_pin ---


@pytest.mark.asyncio
async def test_set_pin_success(uow, user_data):
	"""Успешная установка PIN-кода."""
	user, contact = user_data
	uow.users.get_user_with_contact.return_value = (user, contact)

	await set_pin(uow, user.id, "5678")

	assert user.pin_hash is not None
	assert uow.committed is True
	assert any(e.action == "set_pin" for e in uow.events)


@pytest.mark.asyncio
async def test_set_pin_not_found(uow):
	"""Ошибка при установке PIN-кода несуществующему пользователю."""
	uow.users.get_user_with_contact.side_effect = AuthNotFound("User not found")

	with pytest.raises(AuthNotFound):
		await set_pin(uow, uuid4(), "1111")
