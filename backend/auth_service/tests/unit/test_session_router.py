import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import HTTPException

from auth_service.session.router import set_pin, logout, logout_all, self_block
from auth_service.session.service import (
    AuthAlreadyBlocked,
    AuthNotFound,
)
from shared.schemas.auth import SetPinRequest


@pytest.mark.asyncio
@patch("auth_service.session.router.service.set_pin")
async def test_set_pin_success(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    payload = SetPinRequest(pin="1234")
    
    res = await set_pin(body=payload, user_id=user_id, session=session)
    assert res.message == "PIN-код успешно обновлён."
    mock_svc.assert_awaited_once_with(session, user_id, "1234")


@pytest.mark.asyncio
@patch("auth_service.session.router.service.set_pin")
async def test_set_pin_error(mock_svc):
    session = AsyncMock()
    mock_svc.side_effect = AuthNotFound("x")
    
    with pytest.raises(AuthNotFound) as exc:
        await set_pin(body=SetPinRequest(pin="1234"), user_id=uuid4(), session=session)
    assert "x" in str(exc.value)


@pytest.mark.asyncio
@patch("auth_service.session.router.service.logout")
async def test_logout_success(mock_svc):
    res = await logout("tok")
    assert res.message == "Сеанс успешно завершён."
    mock_svc.assert_awaited_once_with("tok")


@pytest.mark.asyncio
@patch("auth_service.session.router.service.logout_all")
async def test_logout_all_success(mock_svc):
    u_id = uuid4()
    res = await logout_all(u_id)
    assert res.message == "Все активные сессии завершены."
    mock_svc.assert_awaited_once_with(u_id)


@pytest.mark.asyncio
@patch("auth_service.session.router.service.self_block")
async def test_self_block_success(mock_svc):
    session = AsyncMock()
    u_id = uuid4()
    
    res = await self_block(user_id=u_id, session=session)
    assert "Аккаунт заблокирован" in res.message
    mock_svc.assert_awaited_once_with(session, u_id)


@pytest.mark.asyncio
@patch("auth_service.session.router.service.self_block")
async def test_self_block_error(mock_svc):
    session = AsyncMock()
    mock_svc.side_effect = AuthAlreadyBlocked("x")
    
    with pytest.raises(AuthAlreadyBlocked) as exc:
        await self_block(user_id=uuid4(), session=session)
    assert "x" in str(exc.value)
