import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import HTTPException

from auth_service.unlock.router import request_unlock, confirm_unlock
from auth_service.unlock.service import (
    AuthInvalidCode,
    AuthNotBlocked,
    AuthNotFound,
)
from shared.schemas.unlock import RequestUnlockRequest, UnlockRequest


@pytest.mark.asyncio
@patch("auth_service.unlock.router.service.request_unlock")
async def test_request_unlock_success(mock_svc):
    session = AsyncMock()
    body = RequestUnlockRequest(email="a@a.com")
    
    res = await request_unlock(body, session)
    assert "отправлен" in res.message
    mock_svc.assert_awaited_once_with(session, "a@a.com")


@pytest.mark.asyncio
@patch("auth_service.unlock.router.service.request_unlock")
async def test_request_unlock_error(mock_svc):
    session = AsyncMock()
    mock_svc.side_effect = AuthNotBlocked("x")
    
    with pytest.raises(AuthNotBlocked) as exc:
        await request_unlock(RequestUnlockRequest(email="a@a.com"), session)
    assert "x" in str(exc.value)


@pytest.mark.asyncio
@patch("auth_service.unlock.router.service.confirm_unlock")
async def test_unlock_success(mock_svc):
    session = AsyncMock()
    body = UnlockRequest(email="a@a.com", code="123456")
    
    res = await confirm_unlock(body, session)
    assert "успешно разблокирован" in res.message
    mock_svc.assert_awaited_once_with(session, "a@a.com", "123456")


@pytest.mark.asyncio
@patch("auth_service.unlock.router.service.confirm_unlock")
async def test_unlock_error(mock_svc):
    session = AsyncMock()
    mock_svc.side_effect = AuthInvalidCode("x")
    
    with pytest.raises(AuthInvalidCode) as exc:
        await confirm_unlock(UnlockRequest(email="a@a.com", code="123456"), session)
    assert "x" in str(exc.value)
