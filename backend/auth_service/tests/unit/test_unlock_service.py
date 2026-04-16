from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from auth_service.core.exceptions import (
	AuthInvalidCode,
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
	"""Фикстура для пользователя."""
	user = models.User(id=uuid4(), status="blocked")
	contact = models.Contact(client_id=user.id, email="test@test.com", phone="+79997776655")
	return user, contact


@pytest.mark.asyncio
async def test_request_unlock_user_not_found(uow):
	"""Ошибка при запросе восстановления несуществующего пользователя."""
	uow.users.get_by_phone.return_value = None

	with pytest.raises(AuthNotFound):
		await request_unlock(uow, "+70000000000")


@pytest.mark.asyncio
@patch("auth_service.services.unlock.unlock_codes")
async def test_request_unlock_success(mock_codes, uow, user_contact_tuple):
	"""Успешный запрос кода восстановления (отправка на Email по номеру телефона)."""
	mock_codes.save_unlock_code = AsyncMock()
	mock_codes.generate_code.return_value = "112233"
	user, contact = user_contact_tuple
	uow.users.get_by_phone.return_value = (user, contact)

	await request_unlock(uow, contact.phone)

	mock_codes.save_unlock_code.assert_awaited_once_with(user.id, "112233")
	assert uow.committed is True
	assert any(e.type == "unlock_code" and e.variables["code"] == "112233" for e in uow.events)


@pytest.mark.asyncio
@patch("auth_service.services.unlock.unlock_codes")
async def test_confirm_unlock_invalid_code(mock_codes, uow, user_contact_tuple):
	"""Ошибка при вводе неверного кода восстановления."""
	user, contact = user_contact_tuple
	uow.users.get_by_phone = AsyncMock(return_value=(user, contact))
	mock_codes.verify_unlock_code = AsyncMock(return_value=False)

	with pytest.raises(AuthInvalidCode):
		await confirm_unlock(uow, contact.phone, "wrong_code", "1234")


@pytest.mark.asyncio
@patch("auth_service.services.unlock.bcrypt")
@patch("auth_service.services.unlock.rate_limit")
@patch("auth_service.services.unlock.unlock_codes")
async def test_confirm_unlock_success(mock_codes, mock_rate_limit, mock_bcrypt, uow, user_contact_tuple):
	"""Успешное подтверждение восстановления со сменой PIN и разморозкой счетов."""
	user, contact = user_contact_tuple
	uow.users.get_by_phone = AsyncMock(return_value=(user, contact))
	mock_codes.verify_unlock_code = AsyncMock(return_value=True)
	mock_rate_limit.reset = AsyncMock()
	mock_bcrypt.hashpw.return_value = b"new_hash"
	mock_bcrypt.gensalt.return_value = b"salt"

	# Имитация 'системно' замороженных счетов
	acc1 = models.BankAccount(status="frozen", frozen_by="system")
	uow.users.get_system_frozen_accounts.return_value = [acc1]

	await confirm_unlock(uow, contact.phone, "112233", "5566")

	assert user.status == "active"
	assert user.pin_hash == "new_hash"
	assert acc1.status == "open"

	assert uow.committed is True
	mock_rate_limit.reset.assert_awaited_once_with(contact.phone)

	assert any(e.type == "pin_changed" for e in uow.events)
	assert any(getattr(e, "action", None) == "recovery_success" for e in uow.events)
