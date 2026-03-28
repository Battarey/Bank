import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, UTC

from auth_service.login.service import (
    _find_user_by_phone,
    _verify_pin,
    _generate_token,
    _lock_account,
    login_pin,
    AuthError,
    AuthNotFound,
    AuthForbidden,
    AuthCooldown,
    AuthAccountLocked,
)
from shared import models

@pytest.mark.asyncio
async def test_find_user_by_phone_not_found(mock_session):
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.execute.return_value = mock_result
    
    with pytest.raises(AuthNotFound):
        await _find_user_by_phone(mock_session, "+79991234567")

@pytest.mark.asyncio
async def test_find_user_by_phone_success(mock_session):
    user = models.User(id=uuid4())
    contact = models.Contact(client_id=uuid4())
    
    # Mocking row.tuple()
    row_mock = MagicMock()
    row_mock.tuple.return_value = (user, contact)
    
    mock_result = MagicMock()
    mock_result.first.return_value = row_mock
    mock_session.execute.return_value = mock_result
    
    u, c = await _find_user_by_phone(mock_session, "+79991234567")
    assert u == user
    assert c == contact

def test_verify_pin():
    import bcrypt
    password = b"1234"
    hashed = bcrypt.hashpw(password, bcrypt.gensalt()).decode()
    assert _verify_pin("1234", hashed) is True
    assert _verify_pin("4321", hashed) is False

def test_generate_token():
    t1 = _generate_token()
    t2 = _generate_token()
    assert len(t1) > 20
    assert t1 != t2

@pytest.mark.asyncio
@patch("auth_service.login.service.publish")
async def test_lock_account_success(mock_publish, mock_session):
    user = models.User(id=uuid4(), status="active")
    acc1 = models.BankAccount(status="open")
    acc2 = models.BankAccount(status="open")
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [acc1, acc2]
    mock_session.execute.return_value = mock_result
    
    await _lock_account(mock_session, user, "test@test.com")
    
    assert user.status == "blocked"
    assert acc1.status == "frozen"
    assert acc1.frozen_by == "system"
    assert acc2.status == "frozen"
    
    mock_session.commit.assert_awaited_once()
    assert mock_publish.call_count == 2  # email log + auth log

@pytest.mark.asyncio
@patch("auth_service.login.service.publish")
async def test_lock_account_commit_error(mock_publish, mock_session):
    user = models.User(id=uuid4(), status="active")
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    mock_session.commit.side_effect = Exception("db_error")
    
    with pytest.raises(Exception):
        await _lock_account(mock_session, user, "test@test.com")
    
    mock_session.rollback.assert_awaited_once()
    mock_publish.assert_not_awaited()

# login_pin tests

@pytest.fixture
def user_tuple():
    user = models.User(id=uuid4(), status="active", pin_hash="hashed_1234")
    contact = models.Contact(client_id=uuid4(), email="test@test.com", phone="+79991234567")
    return user, contact

@pytest.mark.asyncio
@patch("auth_service.login.service._find_user_by_phone")
async def test_login_pin_blocked_user(mock_find, mock_session, user_tuple):
    user, contact = user_tuple
    user.status = "blocked"
    mock_find.return_value = (user, contact)
    
    with pytest.raises(AuthAccountLocked):
        await login_pin(mock_session, "+79991234567", "1234")

@pytest.mark.asyncio
@patch("auth_service.login.service.rate_limit.check_cooldown")
@patch("auth_service.login.service.rate_limit.get_total_failures")
@patch("auth_service.login.service._find_user_by_phone")
async def test_login_pin_in_cooldown(mock_find, mock_total, mock_cooldown, mock_session, user_tuple):
    mock_find.return_value = user_tuple
    mock_cooldown.return_value = 60
    mock_total.return_value = 5
    
    with pytest.raises(AuthCooldown):
        await login_pin(mock_session, "+79991234567", "1234")

@pytest.mark.asyncio
@patch("auth_service.login.service.rate_limit.check_cooldown")
@patch("auth_service.login.service._find_user_by_phone")
async def test_login_pin_no_pin_hash(mock_find, mock_cooldown, mock_session, user_tuple):
    user, contact = user_tuple
    user.pin_hash = None
    mock_find.return_value = (user, contact)
    mock_cooldown.return_value = None
    
    with pytest.raises(AuthForbidden, match="PIN-код не установлен"):
        await login_pin(mock_session, "+79991234567", "1234")

@pytest.mark.asyncio
@patch("auth_service.login.service._verify_pin")
@patch("auth_service.login.service.rate_limit.record_failure")
@patch("auth_service.login.service.rate_limit.check_cooldown")
@patch("auth_service.login.service._find_user_by_phone")
async def test_login_pin_wrong_pin_warn(mock_find, mock_cooldown, mock_record, mock_verify, mock_session, user_tuple):
    mock_find.return_value = user_tuple
    mock_cooldown.return_value = None
    mock_verify.return_value = False
    mock_record.return_value = (3, False, False) # total, cooldown_started, should_lock
    
    with pytest.raises(AuthForbidden, match="Неверный PIN-код"):
        await login_pin(mock_session, "+79991234567", "1111")
    mock_record.assert_awaited_once()

@pytest.mark.asyncio
@patch("auth_service.login.service._verify_pin")
@patch("auth_service.login.service.rate_limit.record_failure")
@patch("auth_service.login.service.rate_limit.check_cooldown")
@patch("auth_service.login.service._find_user_by_phone")
async def test_login_pin_wrong_pin_cooldown(mock_find, mock_cooldown, mock_record, mock_verify, mock_session, user_tuple):
    mock_find.return_value = user_tuple
    mock_cooldown.return_value = None
    mock_verify.return_value = False
    mock_record.return_value = (5, True, False) # total, cooldown_started, should_lock
    
    with pytest.raises(AuthCooldown):
        await login_pin(mock_session, "+79991234567", "1111")

@pytest.mark.asyncio
@patch("auth_service.login.service._lock_account")
@patch("auth_service.login.service._verify_pin")
@patch("auth_service.login.service.rate_limit.record_failure")
@patch("auth_service.login.service.rate_limit.check_cooldown")
@patch("auth_service.login.service._find_user_by_phone")
async def test_login_pin_wrong_pin_lock(mock_find, mock_cooldown, mock_record, mock_verify, mock_lock, mock_session, user_tuple):
    mock_find.return_value = user_tuple
    mock_cooldown.return_value = None
    mock_verify.return_value = False
    mock_record.return_value = (15, False, True) # total, cooldown_started, should_lock
    
    with pytest.raises(AuthAccountLocked):
        await login_pin(mock_session, "+79991234567", "1111")
    mock_lock.assert_awaited_once_with(mock_session, user_tuple[0], user_tuple[1].email)

@pytest.mark.asyncio
@patch("auth_service.login.service.publish")
@patch("auth_service.login.service.session_tokens.save_token")
@patch("auth_service.login.service._generate_token")
@patch("auth_service.login.service.rate_limit.reset")
@patch("auth_service.login.service._verify_pin")
@patch("auth_service.login.service.rate_limit.check_cooldown")
@patch("auth_service.login.service._find_user_by_phone")
async def test_login_pin_success(mock_find, mock_cooldown, mock_verify, mock_reset, mock_gen, mock_save, mock_publish, mock_session, user_tuple):
    mock_find.return_value = user_tuple
    mock_cooldown.return_value = None
    mock_verify.return_value = True
    mock_gen.return_value = "fake_token"
    
    token, u_id = await login_pin(mock_session, "+79991234567", "1234")
    
    assert token == "fake_token"
    assert u_id == user_tuple[0].id
    mock_reset.assert_awaited_once_with("+79991234567")
    mock_save.assert_awaited_once_with("fake_token", user_tuple[0].id, payload={"has_pin": "true"})
    assert mock_publish.call_count == 2
