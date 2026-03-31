import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import HTTPException

from auth_service.login.router import login_pin
from auth_service.login.service import (
    AuthAccountLocked,
    AuthCooldown,
    AuthError,
    AuthForbidden,
    AuthNotFound,
)
from shared.schemas.auth import LoginPinRequest


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
    
    with pytest.raises(AuthForbidden) as exc:
        await login_pin(body=payload, session=session)
        
    assert "wrong pin" in str(exc.value)
