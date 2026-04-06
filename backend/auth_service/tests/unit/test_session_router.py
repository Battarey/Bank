import pytest
from unittest.mock import patch
from uuid import uuid4

from auth_service.session.router import logout, logout_all, self_block
from auth_service.exceptions import (
    AuthAlreadyBlocked,
    AuthNotFound,
)

@pytest.mark.asyncio
@patch("auth_service.session.router.service.logout")
async def test_logout_success(mock_svc):
    """Успешный выход через роутер с передачей токена из заголовка."""
    res = await logout(x_session_token="tok")
    assert res.message == "Сеанс успешно завершён."
    mock_svc.assert_awaited_once_with("tok")

@pytest.mark.asyncio
@patch("auth_service.session.router.service.logout_all")
async def test_logout_all_success(mock_svc):
    """Успешный выход из всех устройств пользователя."""
    user_id = uuid4()
    res = await logout_all(user_id=user_id)
    assert res.message == "Все активные сессии завершены."
    mock_svc.assert_awaited_once_with(user_id)

@pytest.mark.asyncio
@patch("auth_service.session.router.service.self_block")
async def test_self_block_success(mock_svc, uow):
    """Успешная самоблокировка с использованием uow."""
    user_id = uuid4()
    
    res = await self_block(user_id=user_id, uow=uow)
    assert "заблокирован" in res.message
    mock_svc.assert_awaited_once_with(uow, user_id)

@pytest.mark.asyncio
@patch("auth_service.session.router.service.self_block")
async def test_self_block_error(mock_svc, uow):
    """Ошибка самоблокировки (например, уже заблокирован)."""
    user_id = uuid4()
    mock_svc.side_effect = AuthAlreadyBlocked("x")
    
    with pytest.raises(AuthAlreadyBlocked) as exc:
        await self_block(user_id=user_id, uow=uow)
    assert "x" in str(exc.value)
