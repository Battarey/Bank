import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import HTTPException

from auth_service.unlock.router import _raise, request_unlock, unlock
from auth_service.unlock.service import (
    UnlockError,
    UnlockInvalidCode,
    UnlockNotBlocked,
    UnlockNotFound,
)
from shared.schemas.unlock import RequestUnlockRequest, UnlockRequest

def test_raise_exceptions():
    with pytest.raises(HTTPException) as exc:
        _raise(UnlockNotFound("x"))
    assert exc.value.status_code == 404
    
    with pytest.raises(HTTPException) as exc:
        _raise(UnlockNotBlocked("x"))
    assert exc.value.status_code == 409
    
    with pytest.raises(HTTPException) as exc:
        _raise(UnlockInvalidCode("x"))
    assert exc.value.status_code == 400
    
    with pytest.raises(HTTPException) as exc:
        _raise(UnlockError("x"))
    assert exc.value.status_code == 400

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
    mock_svc.side_effect = UnlockNotBlocked("x")
    
    with pytest.raises(HTTPException) as exc:
        await request_unlock(RequestUnlockRequest(email="a@a.com"), session)
    assert exc.value.status_code == 409

@pytest.mark.asyncio
@patch("auth_service.unlock.router.service.unlock_account")
async def test_unlock_success(mock_svc):
    session = AsyncMock()
    body = UnlockRequest(email="a@a.com", code="123456")
    
    res = await unlock(body, session)
    assert "успешно разблокирован" in res.message
    mock_svc.assert_awaited_once_with(session, "a@a.com", "123456")

@pytest.mark.asyncio
@patch("auth_service.unlock.router.service.unlock_account")
async def test_unlock_error(mock_svc):
    session = AsyncMock()
    mock_svc.side_effect = UnlockInvalidCode("x")
    
    with pytest.raises(HTTPException) as exc:
        await unlock(UnlockRequest(email="a@a.com", code="123456"), session)
    assert exc.value.status_code == 400
