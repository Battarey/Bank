from unittest.mock import patch
from uuid import uuid4

import pytest

from auth_service.core.exceptions import (
	AuthInvalidCode,
	AuthNotFound,
)
from auth_service.api.unlock import confirm_unlock, request_unlock
from shared.schemas import RequestUnlockRequest, UnlockRequest


@pytest.mark.asyncio
@patch("auth_service.api.unlock.service.request_unlock")
async def test_request_unlock_success(mock_svc, uow):
	"""Успешный запрос восстановления через роутер."""
	body = RequestUnlockRequest(phone="+79998887766")

	res = await request_unlock(body=body, uow=uow)
	assert "отправлен" in res.message.lower()
	mock_svc.assert_awaited_once_with(uow, "+79998887766")


@pytest.mark.asyncio
@patch("auth_service.api.unlock.service.request_unlock")
async def test_request_unlock_error(mock_svc, uow):
	"""Ошибка запроса восстановления (пользователь не найден)."""
	mock_svc.side_effect = AuthNotFound("User not found")
	body = RequestUnlockRequest(phone="+70000000000")

	with pytest.raises(AuthNotFound) as exc:
		await request_unlock(body=body, uow=uow)
	assert "not found" in str(exc.value).lower()


@pytest.mark.asyncio
@patch("auth_service.api.unlock.service.confirm_unlock")
async def test_confirm_unlock_success(mock_svc, uow):
	"""Успешное подтверждение восстановления и смены PIN через роутер."""
	body = UnlockRequest(phone="+79998887766", code="123456", new_pin="5566")

	res = await confirm_unlock(body=body, uow=uow)
	assert "успешно восстановлен" in res.message.lower()
	mock_svc.assert_awaited_once_with(uow, "+79998887766", "123456", "5566")


@pytest.mark.asyncio
@patch("auth_service.api.unlock.service.confirm_unlock")
async def test_confirm_unlock_error(mock_svc, uow):
	"""Ошибка подтверждения восстановления (например, неверный код)."""
	mock_svc.side_effect = AuthInvalidCode("Invalid")
	body = UnlockRequest(phone="+79998887766", code="123456", new_pin="5566")

	with pytest.raises(AuthInvalidCode) as exc:
		await confirm_unlock(body=body, uow=uow)
	assert "invalid" in str(exc.value).lower()
