import pytest
from unittest.mock import patch

from auth_service.unlock.router import request_unlock, confirm_unlock
from auth_service.exceptions import (
    AuthInvalidCode,
    AuthNotBlocked,
    AuthNotFound,
)
from shared.schemas import RequestUnlockRequest, UnlockRequest

@pytest.mark.asyncio
@patch("auth_service.unlock.router.service.request_unlock")
async def test_request_unlock_success(mock_svc, uow):
    """Успешный запрос когда через роутер с использованием uow."""
    body = RequestUnlockRequest(email="a@a.com")
    
    res = await request_unlock(body=body, uow=uow)
    assert "отправлен" in res.message
    mock_svc.assert_awaited_once_with(uow, "a@a.com")

@pytest.mark.asyncio
@patch("auth_service.unlock.router.service.request_unlock")
async def test_request_unlock_error(mock_svc, uow):
    """Ошибка запроса разблокировки через роутер."""
    mock_svc.side_effect = AuthNotBlocked("Not blocked")
    body = RequestUnlockRequest(email="a@a.com")
    
    with pytest.raises(AuthNotBlocked) as exc:
        await request_unlock(body=body, uow=uow)
    assert "not blocked" in str(exc.value).lower()

@pytest.mark.asyncio
@patch("auth_service.unlock.router.service.confirm_unlock")
async def test_confirm_unlock_success(mock_svc, uow):
    """Успешная разблокировка через роутер."""
    body = UnlockRequest(email="a@a.com", code="123456")
    
    res = await confirm_unlock(body=body, uow=uow)
    assert "успешно разблокирован" in res.message
    mock_svc.assert_awaited_once_with(uow, "a@a.com", "123456")

@pytest.mark.asyncio
@patch("auth_service.unlock.router.service.confirm_unlock")
async def test_confirm_unlock_error(mock_svc, uow):
    """Ошибка подтверждения разблокировки через роутер."""
    mock_svc.side_effect = AuthInvalidCode("Invalid")
    body = UnlockRequest(email="a@a.com", code="123456")
    
    with pytest.raises(AuthInvalidCode) as exc:
        await confirm_unlock(body=body, uow=uow)
    assert "invalid" in str(exc.value).lower()
