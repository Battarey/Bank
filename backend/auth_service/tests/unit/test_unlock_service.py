from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from auth_service.core.exceptions import (
	AuthInvalidCode,
	AuthNotBlocked,
	AuthNotFound,
)
from auth_service.services.unlock import (
	confirm_unlock,
	request_unlock,
)
from shared import models

# --- Тесты unlock_codes (request_unlock / confirm_unlock) ---


@pytest.fixture
def user_contact_tuple():
	"""Фикстура для заблокированного пользователя."""
	user = models.User(id=uuid4(), status="blocked")
	contact = models.Contact(client_id=user.id, email="blocked@test.com", phone="+79997776655")
	return user, contact


@pytest.mark.asyncio
async def test_request_unlock_user_not_found(uow):
	"""Ошибка при запросе разблокировки несуществующего пользователя."""
	uow.users.get_by_email.return_value = None

	with pytest.raises(AuthNotFound):
		await request_unlock(uow, "missing@test.com")


@pytest.mark.asyncio
async def test_request_unlock_not_blocked(uow, user_contact_tuple):
	"""Ошибка, если аккаунт при запросе разблокировки не заблокирован."""
	user, contact = user_contact_tuple
	user.status = "active"
	uow.users.get_by_email.return_value = (user, contact)

	with pytest.raises(AuthNotBlocked):
		await request_unlock(uow, contact.email)


@pytest.mark.asyncio
@patch("auth_service.services.unlock.unlock_codes")
async def test_request_unlock_success(mock_codes, uow, user_contact_tuple):
	"""Успешный запрос когда через роутер с использованием uow."""
	mock_codes.save_unlock_code = AsyncMock()
	mock_codes.generate_code.return_value = "112233"
	user, contact = user_contact_tuple
	uow.users.get_by_email.return_value = (user, contact)

	await request_unlock(uow, contact.email)

	mock_codes.save_unlock_code.assert_awaited_once_with(user.id, "112233")
	assert uow.committed is True
	assert any(e.type == "unlock_code" and e.variables["code"] == "112233" for e in uow.events)


@pytest.mark.asyncio
@patch("auth_service.services.unlock.unlock_codes")
async def test_confirm_unlock_invalid_code(mock_codes, uow, user_contact_tuple):
	"""Ошибка при вводе неверного кода разблокировки."""
	user, contact = user_contact_tuple
	uow.users.get_by_email = AsyncMock(return_value=(user, contact))
	mock_codes.verify_unlock_code = AsyncMock(return_value=False)

	with pytest.raises(AuthInvalidCode):
		await confirm_unlock(uow, contact.email, "wrong_code")


@pytest.mark.asyncio
@patch("auth_service.services.unlock.rate_limit")
@patch("auth_service.services.unlock.unlock_codes")
async def test_confirm_unlock_success(mock_codes, mock_rate_limit, uow, user_contact_tuple):
	"""Успешное подтверждение разблокировки с разморозкой счетов."""
	user, contact = user_contact_tuple
	uow.users.get_by_email = AsyncMock(return_value=(user, contact))
	mock_codes.verify_unlock_code = AsyncMock(return_value=True)
	mock_rate_limit.reset = AsyncMock()

	# Имитация 'системно' замороженных счетов
	acc1 = models.BankAccount(status="frozen", frozen_by="system")
	uow.users.get_system_frozen_accounts.return_value = [acc1]

	await confirm_unlock(uow, contact.email, "112233")

	assert user.status == "active"
	assert acc1.status == "open"
	assert acc1.frozen_by is None

	assert uow.committed is True
	# Проверка сброса лимитов входа ПОСЛЕ коммита
	mock_rate_limit.reset.assert_awaited_once_with(contact.phone)

	assert any(e.type == "account_unlocked" for e in uow.events)
	assert any(getattr(e, "action", None) == "unlock" for e in uow.events)
