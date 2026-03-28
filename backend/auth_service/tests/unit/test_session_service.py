import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from auth_service.session.service import (
    _hash_pin,
    set_pin,
    logout,
    logout_all,
    self_block,
    SessionError,
    SessionNotFound,
    SessionAlreadyBlocked,
)
from shared import models

def test_hash_pin():
    hashed = _hash_pin("1234")
    assert hashed.startswith("$2")
    assert "1234" not in hashed

@pytest.mark.asyncio
async def test_set_pin_not_found(mock_session):
    mock_session.get.return_value = None
    with pytest.raises(SessionNotFound):
        await set_pin(mock_session, uuid4(), "1234")

@pytest.mark.asyncio
@patch("auth_service.session.service.publish")
async def test_set_pin_db_error(mock_publish, mock_session):
    user = models.User(id=uuid4())
    mock_session.get.side_effect = [user]
    mock_session.commit.side_effect = Exception("failed")
    
    with pytest.raises(Exception):
        await set_pin(mock_session, uuid4(), "1234")
    mock_session.rollback.assert_awaited_once()

@pytest.mark.asyncio
@patch("auth_service.session.service.publish")
async def test_set_pin_success(mock_publish, mock_session):
    user = models.User(id=uuid4())
    contact = models.Contact(email="a@a.com")
    mock_session.get.side_effect = [user, contact]
    
    await set_pin(mock_session, uuid4(), "1234")
    
    assert user.pin_hash is not None
    mock_session.commit.assert_awaited_once()
    assert mock_publish.call_count == 2

@pytest.mark.asyncio
@patch("auth_service.session.service.publish")
async def test_set_pin_publish_error(mock_publish, mock_session):
    user = models.User(id=uuid4())
    contact = models.Contact(email="a@a.com")
    mock_session.get.side_effect = [user, contact]
    mock_publish.side_effect = Exception("error")
    
    with pytest.raises(Exception):
        await set_pin(mock_session, uuid4(), "1234")
    assert user.pin_hash is not None

@pytest.mark.asyncio
@patch("auth_service.session.service.session_tokens.delete_token")
async def test_logout(mock_delete):
    await logout("token123")
    mock_delete.assert_awaited_once_with("token123")

@pytest.mark.asyncio
@patch("auth_service.session.service.session_tokens.revoke_all")
async def test_logout_all(mock_revoke):
    u_id = uuid4()
    await logout_all(u_id)
    mock_revoke.assert_awaited_once_with(u_id)

@pytest.mark.asyncio
async def test_self_block_not_found(mock_session):
    mock_session.get.return_value = None
    with pytest.raises(SessionNotFound):
        await self_block(mock_session, uuid4(), "tok")

@pytest.mark.asyncio
async def test_self_block_already_blocked(mock_session):
    user = models.User(status="blocked")
    mock_session.get.return_value = user
    with pytest.raises(SessionAlreadyBlocked):
        await self_block(mock_session, uuid4(), "tok")

@pytest.mark.asyncio
@patch("auth_service.session.service.publish")
@patch("auth_service.session.service.session_tokens.revoke_all")
async def test_self_block_success(mock_revoke, mock_publish, mock_session):
    user = models.User(id=uuid4(), status="active")
    contact = models.Contact(email="a@a.com")
    
    def get_se(m, pk):
        if m == models.User: return user
        if m == models.Contact: return contact
        return None
    mock_session.get.side_effect = get_se
    
    acc1 = models.BankAccount(status="open")
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [acc1]
    mock_session.execute.return_value = mock_result
    
    await self_block(mock_session, user.id, "tok")
    
    assert user.status == "blocked"
    assert acc1.status == "frozen"
    assert acc1.frozen_by == "system"
    mock_session.commit.assert_awaited_once()
    mock_revoke.assert_awaited_once_with(user.id)
    assert mock_publish.call_count == 2

@pytest.mark.asyncio
@patch("auth_service.session.service.session_tokens.revoke_all")
async def test_self_block_db_error(mock_revoke, mock_session):
    user = models.User(id=uuid4(), status="active")
    mock_session.get.side_effect = [user]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    mock_session.commit.side_effect = Exception("err")
    
    with pytest.raises(Exception):
        await self_block(mock_session, user.id, "tok")
    
    mock_session.rollback.assert_awaited_once()
    mock_revoke.assert_not_awaited()

@pytest.mark.asyncio
@patch("auth_service.session.service.publish")
@patch("auth_service.session.service.session_tokens.revoke_all")
async def test_self_block_publish_error(mock_revoke, mock_publish, mock_session):
    user = models.User(id=uuid4(), status="active")
    contact = models.Contact(email="a@a.com")
    
    def get_se(m, pk):
        if m == models.User: return user
        if m == models.Contact: return contact
        return None
    mock_session.get.side_effect = get_se
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    
    mock_publish.side_effect = Exception("failed_pub")
    
    await self_block(mock_session, user.id, "tok")
    assert user.status == "blocked"
