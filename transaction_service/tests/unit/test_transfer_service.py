import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from uuid import uuid4
from sqlalchemy.exc import IntegrityError

from shared import models
from transaction_service.transfer.service import transfer
from transaction_service.exceptions import (
    SameAccountTransfer, AccountNotFound, AccountFrozen,
    AccountNotOpen, InsufficientFunds, SecurityViolation,
    RateUnavailable, TransactionConflict,
)


def _make_account(status="open", balance=Decimal("1000"), client_id=None, currency="RUB"):
    acc = models.BankAccount()
    acc.id = uuid4()
    acc.client_id = client_id or uuid4()
    acc.status = status
    acc.balance = balance
    acc.currency = currency
    acc.account_number = "40817810000000000001"
    acc.frozen_by = None
    acc.frozen_at = None
    acc.freeze_reason = None
    return acc


@pytest.mark.asyncio
async def test_transfer_same_account(mock_session):
    acc_id = uuid4()
    with pytest.raises(SameAccountTransfer):
        await transfer(mock_session, uuid4(), acc_id, acc_id, Decimal("100"), None)


@pytest.mark.asyncio
async def test_transfer_from_not_found(mock_session):
    user_id = uuid4()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    with pytest.raises(AccountNotFound):
        await transfer(mock_session, user_id, uuid4(), uuid4(), Decimal("100"), None)


@pytest.mark.asyncio
async def test_transfer_from_frozen(mock_session):
    user_id = uuid4()
    from_acc = _make_account(status="frozen", client_id=user_id)
    to_acc = _make_account(status="open")
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [from_acc, to_acc]
    mock_session.execute.return_value = mock_result

    with pytest.raises(AccountFrozen):
        await transfer(mock_session, user_id, from_acc.id, to_acc.id, Decimal("100"), None)


@pytest.mark.asyncio
async def test_transfer_insufficient_funds(mock_session):
    user_id = uuid4()
    from_acc = _make_account(status="open", balance=Decimal("10"), client_id=user_id)
    to_acc = _make_account(status="open")
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [from_acc, to_acc]
    mock_session.execute.return_value = mock_result

    with pytest.raises(InsufficientFunds):
        await transfer(mock_session, user_id, from_acc.id, to_acc.id, Decimal("100"), None)


@pytest.mark.asyncio
@patch("transaction_service.security_client.check_transaction")
@patch("transaction_service.transfer.service.publish")
async def test_transfer_success(mock_publish, mock_security, mock_session):
    mock_security.return_value = (True, [])
    user_id = uuid4()
    from_acc = _make_account(status="open", balance=Decimal("1000"), client_id=user_id)
    to_acc = _make_account(status="open", balance=Decimal("500"))
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [from_acc, to_acc]
    mock_session.execute.return_value = mock_result
    mock_session.get.return_value = None

    tx = await transfer(mock_session, user_id, from_acc.id, to_acc.id, Decimal("300"), None)

    assert from_acc.balance == Decimal("700")
    assert to_acc.balance == Decimal("800")
    mock_session.add_all.assert_called_once()


@pytest.mark.asyncio
@patch("transaction_service.security_client.check_transaction")
@patch("transaction_service.transfer.service.publish")
async def test_transfer_security_violation(mock_publish, mock_security, mock_session):
    mock_security.return_value = (False, [{"rule": "large_single_tx"}])
    user_id = uuid4()
    from_acc = _make_account(status="open", balance=Decimal("1000"), client_id=user_id)
    to_acc = _make_account(status="open")
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [from_acc, to_acc]
    mock_session.execute.return_value = mock_result
    mock_session.get.return_value = None

    with pytest.raises(SecurityViolation):
        await transfer(mock_session, user_id, from_acc.id, to_acc.id, Decimal("300"), None)

    assert from_acc.status == "frozen"


@pytest.mark.asyncio
@patch("transaction_service.security_client.check_transaction")
@patch("transaction_service.currency_client.get_rate")
@patch("transaction_service.transfer.service.publish")
async def test_transfer_cross_currency(mock_publish, mock_rate, mock_security, mock_session):
    mock_security.return_value = (True, [])
    mock_rate.return_value = Decimal("0.012")  # RUB → USD
    user_id = uuid4()
    from_acc = _make_account(status="open", balance=Decimal("10000"), client_id=user_id, currency="RUB")
    to_acc = _make_account(status="open", balance=Decimal("100"), currency="USD")
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [from_acc, to_acc]
    mock_session.execute.return_value = mock_result
    mock_session.get.return_value = None

    tx = await transfer(mock_session, user_id, from_acc.id, to_acc.id, Decimal("1000"), None)

    assert from_acc.balance == Decimal("9000")
    # 1000 * 0.012 = 12.00
    assert to_acc.balance == Decimal("112.00")
