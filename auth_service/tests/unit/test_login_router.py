import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import HTTPException

from auth_service.login.router import _raise, login_pin
from auth_service.login.service import (
    AuthAccountLocked,
    AuthCooldown,
    AuthError,
    AuthForbidden,
    AuthNotFound,
)
from shared.schemas.auth import LoginPinRequest


def test_raise_exceptions():
    with pytest.raises(HTTPException) as exc:
        _raise(AuthAccountLocked())
    assert exc.value.status_code == 423
    
    with pytest.raises(HTTPException) as exc:
        _raise(AuthCooldown(retry_after=60, total_failures=5))
    assert exc.value.status_code == 429
    assert exc.value.headers["Retry-After"] == "60"
    
    with pytest.raises(HTTPException) as exc:
        _raise(AuthNotFound("x"))
    assert exc.value.status_code == 404
    
    with pytest.raises(HTTPException) as exc:
        _raise(AuthForbidden("x"))
    assert exc.value.status_code == 401
    
    with pytest.raises(HTTPException) as exc:
        _raise(AuthError("x"))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
@patch("auth_service.login.router.service.login_pin")
async def test_login_pin_success(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    token = "some_token"
    
    mock_svc.return_value = (token, user_id)
    
    payload = LoginPinRequest.model_validate({"phone": "+79991234567", "pin": "1234"})
    res = await login_pin(body=payload, session=session)
    
    assert res.session_token == token
    assert res.user_id == str(user_id)


@pytest.mark.asyncio
@patch("auth_service.login.router.service.login_pin")
async def test_login_pin_error(mock_svc):
    session = AsyncMock()
    mock_svc.side_effect = AuthForbidden("wrong pin")
    
    payload = LoginPinRequest.model_validate({"phone": "+79991234567", "pin": "1234"})
    
    with pytest.raises(HTTPException) as exc:
        await login_pin(body=payload, session=session)
        
    assert exc.value.status_code == 401
