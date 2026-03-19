import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from account_service.close_account.service import (
    _notify_account_closed,
    close_account,
)
from account_service.exceptions import (
    AccountConflict,
    AccountNonZeroBalance,
    AccountNotFound,
    AccountNotOpen,
)
from shared import models

@pytest.mark.asyncio
@patch("account_service.close_account.service.publish")
async def test_notify_account_closed_no_contact(mock_publish, mock_session):
    mock_session.get.return_value = None
    await _notify_account_closed(mock_session, uuid4(), models.BankAccount())
    mock_publish.assert_not_awaited()

@pytest.mark.asyncio
@patch("account_service.close_account.service.publish")
async def test_notify_account_closed_success(mock_publish, mock_session):
    contact = models.Contact(email="a@a.com")
    mock_session.get.return_value = contact
    acc = models.BankAccount(account_number="123")
    await _notify_account_closed(mock_session, uuid4(), acc)
    mock_publish.assert_awaited_once()

@pytest.mark.asyncio
async def test_close_account_not_found(mock_session):
    mock_session.get.return_value = None
    with pytest.raises(AccountNotFound):
        await close_account(mock_session, uuid4(), uuid4())

@pytest.mark.asyncio
async def test_close_account_wrong_owner(mock_session):
    acc = models.BankAccount(client_id=uuid4())
    mock_session.get.return_value = acc
    with pytest.raises(AccountNotFound):
        await close_account(mock_session, uuid4(), uuid4())

@pytest.mark.asyncio
async def test_close_account_not_open(mock_session):
    user_id = uuid4()
    acc = models.BankAccount(client_id=user_id, status="frozen")
    mock_session.get.return_value = acc
    with pytest.raises(AccountNotOpen):
        await close_account(mock_session, user_id, uuid4())

@pytest.mark.asyncio
async def test_close_account_nonzero_balance(mock_session):
    user_id = uuid4()
    acc = models.BankAccount(client_id=user_id, status="open", balance=Decimal("100.00"), currency="RUB")
    mock_session.get.return_value = acc
    with pytest.raises(AccountNonZeroBalance):
        await close_account(mock_session, user_id, uuid4())

@pytest.mark.asyncio
@patch("account_service.close_account.service.publish")
@patch("account_service.close_account.service._notify_account_closed")
async def test_close_account_success(mock_notify, mock_publish, mock_session):
    user_id = uuid4()
    acc = models.BankAccount(id=uuid4(), client_id=user_id, status="open", balance=Decimal("0.00"), account_number="123")
    mock_session.get.return_value = acc
    
    res = await close_account(mock_session, user_id, acc.id)
    
    assert res.status == "closed"
    assert res.closed_at is not None
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(acc)
    mock_notify.assert_awaited_once_with(mock_session, user_id, acc)
    mock_publish.assert_awaited_once()

@pytest.mark.asyncio
@patch("account_service.close_account.service.publish")
@patch("account_service.close_account.service._notify_account_closed")
async def test_close_account_integrity_error(mock_notify, mock_publish, mock_session):
    user_id = uuid4()
    acc = models.BankAccount(id=uuid4(), client_id=user_id, status="open", balance=Decimal("0.00"))
    mock_session.get.return_value = acc
    mock_session.commit.side_effect = IntegrityError("a", "b", "c")
    
    with pytest.raises(AccountConflict):
        await close_account(mock_session, user_id, acc.id)
    mock_session.rollback.assert_awaited_once()

@pytest.mark.asyncio
@patch("account_service.close_account.service.publish")
@patch("account_service.close_account.service._notify_account_closed")
async def test_close_account_publish_error(mock_notify, mock_publish, mock_session):
    user_id = uuid4()
    acc = models.BankAccount(id=uuid4(), client_id=user_id, status="open", balance=Decimal("0.00"))
    mock_session.get.return_value = acc
    mock_publish.side_effect = Exception("error")
    
    res = await close_account(mock_session, user_id, acc.id)
    assert res.status == "closed"
