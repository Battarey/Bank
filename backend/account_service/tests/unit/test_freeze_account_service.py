import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from account_service.freeze_account.service import (
    _notify_frozen,
    _notify_unfrozen,
    freeze_account,
    unfreeze_account,
    cascade_freeze,
    cascade_unfreeze,
)
from account_service.exceptions import (
    AccountAlreadyFrozen,
    AccountNotFound,
    AccountNotFrozen,
    AccountNotOpen,
    UnfreezeNotAllowed,
)
from shared import models

@pytest.mark.asyncio
@patch("account_service.freeze_account.service.publish")
async def test_notify_frozen_no_contact(mock_publish, mock_session):
    mock_session.get.return_value = None
    await _notify_frozen(mock_session, uuid4(), models.BankAccount(), "user", "reason")
    mock_publish.assert_not_awaited()

@pytest.mark.asyncio
@patch("account_service.freeze_account.service.publish")
async def test_notify_frozen_success(mock_publish, mock_session):
    contact = models.Contact(email="a@a.com")
    mock_session.get.return_value = contact
    acc = models.BankAccount(account_number="123")
    await _notify_frozen(mock_session, uuid4(), acc, "user", "reason")
    mock_publish.assert_awaited_once()

@pytest.mark.asyncio
@patch("account_service.freeze_account.service.publish")
async def test_notify_unfrozen_no_contact(mock_publish, mock_session):
    mock_session.get.return_value = None
    await _notify_unfrozen(mock_session, uuid4(), models.BankAccount())
    mock_publish.assert_not_awaited()

@pytest.mark.asyncio
@patch("account_service.freeze_account.service.publish")
async def test_notify_unfrozen_success(mock_publish, mock_session):
    contact = models.Contact(email="a@a.com")
    mock_session.get.return_value = contact
    acc = models.BankAccount(account_number="123")
    await _notify_unfrozen(mock_session, uuid4(), acc)
    mock_publish.assert_awaited_once()

# freeze_account
@pytest.mark.asyncio
async def test_freeze_account_not_found(mock_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    with pytest.raises(AccountNotFound):
        await freeze_account(mock_session, uuid4(), uuid4())

@pytest.mark.asyncio
async def test_freeze_account_already_frozen(mock_session):
    user_id = uuid4()
    acc = models.BankAccount(client_id=user_id, status="frozen")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result
    with pytest.raises(AccountAlreadyFrozen):
        await freeze_account(mock_session, user_id, uuid4())

@pytest.mark.asyncio
async def test_freeze_account_not_open(mock_session):
    user_id = uuid4()
    acc = models.BankAccount(client_id=user_id, status="closed")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result
    with pytest.raises(AccountNotOpen):
        await freeze_account(mock_session, user_id, uuid4())

@pytest.mark.asyncio
@patch("account_service.freeze_account.service.publish")
@patch("account_service.freeze_account.service._notify_frozen")
async def test_freeze_account_success(mock_notify, mock_publish, mock_session):
    user_id = uuid4()
    acc = models.BankAccount(id=uuid4(), client_id=user_id, status="open", account_number="123")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result
    
    res = await freeze_account(mock_session, user_id, acc.id)
    assert res.status == "frozen"
    assert res.frozen_by == "user"
    mock_session.commit.assert_awaited_once()
    mock_notify.assert_awaited_once()
    mock_publish.assert_awaited_once()

@pytest.mark.asyncio
@patch("account_service.freeze_account.service.publish")
@patch("account_service.freeze_account.service._notify_frozen")
async def test_freeze_account_db_error(mock_notify, mock_publish, mock_session):
    user_id = uuid4()
    acc = models.BankAccount(id=uuid4(), client_id=user_id, status="open")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result
    mock_session.commit.side_effect = Exception("failed")
    
    with pytest.raises(Exception):
        await freeze_account(mock_session, user_id, acc.id)
    mock_session.rollback.assert_awaited_once()

@pytest.mark.asyncio
@patch("account_service.freeze_account.service.publish")
@patch("account_service.freeze_account.service._notify_frozen")
async def test_freeze_account_publish_error(mock_notify, mock_publish, mock_session):
    user_id = uuid4()
    acc = models.BankAccount(id=uuid4(), client_id=user_id, status="open")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result
    mock_publish.side_effect = Exception("error")
    
    res = await freeze_account(mock_session, user_id, acc.id)
    assert res.status == "frozen"

# unfreeze_account
@pytest.mark.asyncio
async def test_unfreeze_account_not_found(mock_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    with pytest.raises(AccountNotFound):
        await unfreeze_account(mock_session, uuid4(), uuid4())

@pytest.mark.asyncio
async def test_unfreeze_account_not_frozen(mock_session):
    user_id = uuid4()
    acc = models.BankAccount(client_id=user_id, status="open")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result
    with pytest.raises(AccountNotFrozen):
        await unfreeze_account(mock_session, user_id, uuid4())

@pytest.mark.asyncio
async def test_unfreeze_account_unfreeze_not_allowed(mock_session):
    user_id = uuid4()
    acc = models.BankAccount(client_id=user_id, status="frozen", frozen_by="system")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result
    with pytest.raises(UnfreezeNotAllowed):
        await unfreeze_account(mock_session, user_id, uuid4())

@pytest.mark.asyncio
@patch("account_service.freeze_account.service.publish")
@patch("account_service.freeze_account.service._notify_unfrozen")
async def test_unfreeze_account_success(mock_notify, mock_publish, mock_session):
    user_id = uuid4()
    acc = models.BankAccount(id=uuid4(), client_id=user_id, status="frozen", frozen_by="user", account_number="123")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result
    
    res = await unfreeze_account(mock_session, user_id, acc.id)
    assert res.status == "open"
    assert res.frozen_by is None
    mock_session.commit.assert_awaited_once()
    mock_notify.assert_awaited_once()
    mock_publish.assert_awaited_once()

@pytest.mark.asyncio
@patch("account_service.freeze_account.service.publish")
@patch("account_service.freeze_account.service._notify_unfrozen")
async def test_unfreeze_account_db_error(mock_notify, mock_publish, mock_session):
    user_id = uuid4()
    acc = models.BankAccount(id=uuid4(), client_id=user_id, status="frozen", frozen_by="user")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result
    mock_session.commit.side_effect = Exception("failed")
    
    with pytest.raises(Exception):
        await unfreeze_account(mock_session, user_id, acc.id)
    mock_session.rollback.assert_awaited_once()

@pytest.mark.asyncio
@patch("account_service.freeze_account.service.publish")
@patch("account_service.freeze_account.service._notify_unfrozen")
async def test_unfreeze_account_publish_error(mock_notify, mock_publish, mock_session):
    user_id = uuid4()
    acc = models.BankAccount(id=uuid4(), client_id=user_id, status="frozen", frozen_by="user")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result
    mock_publish.side_effect = Exception("error")
    
    res = await unfreeze_account(mock_session, user_id, acc.id)
    assert res.status == "open"

# cascade
@pytest.mark.asyncio
async def test_cascade_freeze_success(mock_session):
    acc1 = models.BankAccount(status="open")
    acc2 = models.BankAccount(status="open")
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [acc1, acc2]
    mock_session.execute.return_value = mock_result
    
    count = await cascade_freeze(mock_session, uuid4())
    assert count == 2
    assert acc1.status == "frozen"
    assert acc1.frozen_by == "system"
    mock_session.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_cascade_freeze_error(mock_session):
    acc1 = models.BankAccount(status="open")
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [acc1]
    mock_session.execute.return_value = mock_result
    mock_session.commit.side_effect = Exception("x")
    
    with pytest.raises(Exception):
        await cascade_freeze(mock_session, uuid4())
    mock_session.rollback.assert_awaited_once()

@pytest.mark.asyncio
async def test_cascade_unfreeze_success(mock_session):
    acc1 = models.BankAccount(status="frozen", frozen_by="system")
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [acc1]
    mock_session.execute.return_value = mock_result
    
    count = await cascade_unfreeze(mock_session, uuid4())
    assert count == 1
    assert acc1.status == "open"
    assert acc1.frozen_by is None
    mock_session.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_cascade_unfreeze_error(mock_session):
    acc1 = models.BankAccount(status="frozen", frozen_by="system")
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [acc1]
    mock_session.execute.return_value = mock_result
    mock_session.commit.side_effect = Exception("x")
    
    with pytest.raises(Exception):
        await cascade_unfreeze(mock_session, uuid4())
    mock_session.rollback.assert_awaited_once()
