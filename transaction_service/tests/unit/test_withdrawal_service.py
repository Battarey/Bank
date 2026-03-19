import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from uuid import uuid4
from sqlalchemy.exc import IntegrityError

from shared import models
from transaction_service.withdrawal.service import withdraw
from transaction_service.exceptions import (
    AccountNotFound,
    AccountNotOpen,
    AccountFrozen,
    InsufficientFunds,
    SecurityViolation,
    TransactionConflict,
)


def _make_account(status: str = "open", balance: Decimal = Decimal("1000"), client_id=None):
    acc = models.BankAccount()
    acc.id = uuid4()
    acc.client_id = client_id or uuid4()
    acc.status = status
    acc.balance = balance
    acc.currency = "RUB"
    acc.account_number = "40817810000000000001"
    acc.frozen_by = None
    acc.frozen_at = None
    acc.freeze_reason = None
    return acc


@pytest.mark.asyncio
async def test_withdraw_not_found(mock_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with pytest.raises(AccountNotFound):
        await withdraw(mock_session, uuid4(), uuid4(), Decimal("100"), None)


@pytest.mark.asyncio
async def test_withdraw_frozen(mock_session):
    user_id = uuid4()
    acc = _make_account(status="frozen", client_id=user_id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result

    with pytest.raises(AccountFrozen):
        await withdraw(mock_session, user_id, acc.id, Decimal("100"), None)


@pytest.mark.asyncio
async def test_withdraw_not_open(mock_session):
    user_id = uuid4()
    acc = _make_account(status="closed", client_id=user_id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result

    with pytest.raises(AccountNotOpen):
        await withdraw(mock_session, user_id, acc.id, Decimal("100"), None)


@pytest.mark.asyncio
@patch("transaction_service.security_client.check_transaction")
async def test_withdraw_insufficient_funds(mock_security, mock_session):
    mock_security.return_value = (True, [])
    user_id = uuid4()
    acc = _make_account(status="open", balance=Decimal("50"), client_id=user_id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result

    with pytest.raises(InsufficientFunds):
        await withdraw(mock_session, user_id, acc.id, Decimal("100"), None)


@pytest.mark.asyncio
@patch("transaction_service.deposit.service.publish")
@patch("transaction_service.security_client.check_transaction")
async def test_withdraw_security_violation(mock_security, mock_publish, mock_session):
    mock_security.return_value = (False, [{"rule": "rapid_fire"}])
    user_id = uuid4()
    acc = _make_account(status="open", balance=Decimal("1000"), client_id=user_id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result
    mock_session.get.return_value = None  # нет контакта

    with pytest.raises(SecurityViolation):
        await withdraw(mock_session, user_id, acc.id, Decimal("100"), None)

    assert acc.status == "frozen"


@pytest.mark.asyncio
@patch("transaction_service.withdrawal.service.publish")
@patch("transaction_service.security_client.check_transaction")
async def test_withdraw_success(mock_security, mock_publish, mock_session):
    mock_security.return_value = (True, [])
    user_id = uuid4()
    acc = _make_account(status="open", balance=Decimal("1000"), client_id=user_id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result
    mock_session.get.return_value = None

    tx = await withdraw(mock_session, user_id, acc.id, Decimal("300"), None)

    assert acc.balance == Decimal("700")
    mock_session.add.assert_called_once()


@pytest.mark.asyncio
@patch("transaction_service.security_client.check_transaction")
async def test_withdraw_integrity_error(mock_security, mock_session):
    mock_security.return_value = (True, [])
    user_id = uuid4()
    acc = _make_account(status="open", balance=Decimal("1000"), client_id=user_id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result
    mock_session.commit.side_effect = IntegrityError(None, None, Exception())

    with pytest.raises(TransactionConflict):
        await withdraw(mock_session, user_id, acc.id, Decimal("100"), None)
