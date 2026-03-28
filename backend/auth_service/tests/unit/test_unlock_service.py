import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from auth_service.unlock.service import (
    _find_user_by_email,
    request_unlock,
    unlock_account,
    UnlockError,
    UnlockNotFound,
    UnlockNotBlocked,
    UnlockInvalidCode,
)
from shared import models

@pytest.fixture
def user_contact_tuple():
    u = models.User(id=uuid4(), status="blocked")
    c = models.Contact(client_id=uuid4(), email="test@test.com", phone="+79991234567")
    return u, c

@pytest.mark.asyncio
async def test_find_user_by_email_not_found(mock_session):
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.execute.return_value = mock_result
    
    with pytest.raises(UnlockNotFound):
        await _find_user_by_email(mock_session, "test@test.com")

@pytest.mark.asyncio
async def test_find_user_by_email_success(mock_session, user_contact_tuple):
    row_mock = MagicMock()
    row_mock.tuple.return_value = user_contact_tuple
    mock_result = MagicMock()
    mock_result.first.return_value = row_mock
    mock_session.execute.return_value = mock_result
    
    u, c = await _find_user_by_email(mock_session, "test@test.com")
    assert u.id == user_contact_tuple[0].id

# request_unlock
@pytest.mark.asyncio
@patch("auth_service.unlock.service._find_user_by_email")
async def test_request_unlock_not_blocked(mock_find, mock_session, user_contact_tuple):
    u, c = user_contact_tuple
    u.status = "active"
    mock_find.return_value = (u, c)
    
    with pytest.raises(UnlockNotBlocked):
        await request_unlock(mock_session, c.email)

@pytest.mark.asyncio
@patch("auth_service.unlock.service.publish")
@patch("auth_service.unlock.service.unlock_codes.save_unlock_code")
@patch("auth_service.unlock.service.unlock_codes.generate_code")
@patch("auth_service.unlock.service._find_user_by_email")
async def test_request_unlock_success(mock_find, mock_gen, mock_save, mock_publish, mock_session, user_contact_tuple):
    u, c = user_contact_tuple
    mock_find.return_value = (u, c)
    mock_gen.return_value = "123456"
    
    await request_unlock(mock_session, c.email)
    
    mock_save.assert_awaited_once_with(u.id, "123456")
    mock_publish.assert_awaited_once()

# unlock_account
@pytest.mark.asyncio
@patch("auth_service.unlock.service._find_user_by_email")
async def test_unlock_account_not_blocked(mock_find, mock_session, user_contact_tuple):
    u, c = user_contact_tuple
    u.status = "active"
    mock_find.return_value = (u, c)
    
    with pytest.raises(UnlockNotBlocked):
        await unlock_account(mock_session, c.email, "123456")

@pytest.mark.asyncio
@patch("auth_service.unlock.service.unlock_codes.verify_unlock_code")
@patch("auth_service.unlock.service._find_user_by_email")
async def test_unlock_account_invalid_code(mock_find, mock_verify, mock_session, user_contact_tuple):
    mock_find.return_value = user_contact_tuple
    mock_verify.return_value = False
    
    with pytest.raises(UnlockInvalidCode):
        await unlock_account(mock_session, user_contact_tuple[1].email, "123456")

@pytest.mark.asyncio
@patch("auth_service.unlock.service.publish")
@patch("auth_service.unlock.service.rate_limit.reset")
@patch("auth_service.unlock.service.unlock_codes.verify_unlock_code")
@patch("auth_service.unlock.service._find_user_by_email")
async def test_unlock_account_success(mock_find, mock_verify, mock_reset, mock_publish, mock_session, user_contact_tuple):
    mock_find.return_value = user_contact_tuple
    mock_verify.return_value = True
    
    acc1 = models.BankAccount(status="frozen", frozen_by="system")
    acc2 = models.BankAccount(status="frozen", frozen_by="user")
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [acc1] # only system returned by query
    mock_session.execute.return_value = mock_result
    
    await unlock_account(mock_session, user_contact_tuple[1].email, "123456")
    
    assert user_contact_tuple[0].status == "active"
    assert acc1.status == "open"
    assert acc1.frozen_by is None
    
    mock_session.commit.assert_awaited_once()
    mock_reset.assert_awaited_once_with(user_contact_tuple[1].phone)
    assert mock_publish.call_count == 2

@pytest.mark.asyncio
@patch("auth_service.unlock.service.unlock_codes.verify_unlock_code")
@patch("auth_service.unlock.service._find_user_by_email")
async def test_unlock_account_db_error(mock_find, mock_verify, mock_session, user_contact_tuple):
    mock_find.return_value = user_contact_tuple
    mock_verify.return_value = True
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    
    mock_session.commit.side_effect = Exception("failed")
    
    with pytest.raises(Exception):
        await unlock_account(mock_session, user_contact_tuple[1].email, "123456")
        
    mock_session.rollback.assert_awaited_once()

@pytest.mark.asyncio
@patch("auth_service.unlock.service.publish")
@patch("auth_service.unlock.service.rate_limit.reset")
@patch("auth_service.unlock.service.unlock_codes.verify_unlock_code")
@patch("auth_service.unlock.service._find_user_by_email")
async def test_unlock_account_publish_error(mock_find, mock_verify, mock_reset, mock_publish, mock_session, user_contact_tuple):
    mock_find.return_value = user_contact_tuple
    mock_verify.return_value = True
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    
    mock_publish.side_effect = Exception("err")
    
    with pytest.raises(Exception):
        await unlock_account(mock_session, user_contact_tuple[1].email, "123456")
    assert user_contact_tuple[0].status == "active"
