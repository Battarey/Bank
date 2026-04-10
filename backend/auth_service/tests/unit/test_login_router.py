from unittest.mock import patch
from uuid import uuid4

import pytest

from auth_service.exceptions import (
    AuthForbidden,
    AuthNotFound,
)
from auth_service.login.router import login, set_pin
from shared.schemas import LoginPinRequest, SetPinRequest


@pytest.mark.asyncio
@patch("auth_service.login.router.service.login_pin")
async def test_login_success(mock_svc, uow):
    """Успешный вход через роутер с возвратом токена."""
    user_id = uuid4()
    token = "some_token"
    mock_svc.return_value = (token, user_id)
    
    payload = LoginPinRequest(phone="+79991234567", pin="1234")
    res = await login(body=payload, uow=uow)
    
    assert res.session_token == token
    assert res.user_id == str(user_id)
    mock_svc.assert_awaited_once_with(uow, "+79991234567", "1234")

@pytest.mark.asyncio
@patch("auth_service.login.router.service.login_pin")
async def test_login_error(mock_svc, uow):
    """Ошибка входа через роутер (например, неверный PIN)."""
    mock_svc.side_effect = AuthForbidden("wrong pin")
    payload = LoginPinRequest(phone="+79991234567", pin="1234")
    
    with pytest.raises(AuthForbidden) as exc:
        await login(body=payload, uow=uow)
    assert "wrong pin" in str(exc.value)

@pytest.mark.asyncio
@patch("auth_service.login.router.service.set_pin")
async def test_set_pin_success(mock_svc, uow):
    """Успешная установка PIN через роутер."""
    user_id = uuid4()
    payload = SetPinRequest(pin="4321")
    
    res = await set_pin(body=payload, user_id=user_id, uow=uow)
    
    assert res.message == "PIN-код успешно обновлён."
    mock_svc.assert_awaited_once_with(uow, user_id, "4321")

@pytest.mark.asyncio
@patch("auth_service.login.router.service.set_pin")
async def test_set_pin_error(mock_svc, uow):
    """Ошибка установки PIN (например, пользователь не найден)."""
    user_id = uuid4()
    mock_svc.side_effect = AuthNotFound("User not found")
    
    with pytest.raises(AuthNotFound) as exc:
        await set_pin(body=SetPinRequest(pin="4321"), user_id=user_id, uow=uow)
    assert "not found" in str(exc.value).lower()
