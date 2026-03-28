import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from uuid import uuid4
from sqlalchemy.exc import IntegrityError

from shared import models
from transaction_service.deposit.service import deposit
from transaction_service.exceptions import AccountNotFound, AccountNotOpen, TransactionConflict


def _make_account(status: str = "open", balance: Decimal = Decimal("1000"), client_id=None):
    acc = models.BankAccount()
    acc.id = uuid4()
    acc.client_id = client_id or uuid4()
    acc.status = status
    acc.balance = balance
    acc.currency = "RUB"
    acc.account_number = "40817810000000000001"
    return acc


@pytest.mark.asyncio
async def test_deposit_account_not_found(mock_session):
    """Счёт не найден → AccountNotFound."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with pytest.raises(AccountNotFound):
        await deposit(mock_session, uuid4(), uuid4(), Decimal("100"), None)


@pytest.mark.asyncio
async def test_deposit_account_wrong_user(mock_session):
    """Счёт найден, но принадлежит другому пользователю → AccountNotFound."""
    acc = _make_account()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result

    with pytest.raises(AccountNotFound):
        await deposit(mock_session, uuid4(), acc.id, Decimal("100"), None)


@pytest.mark.asyncio
async def test_deposit_account_wrong_status(mock_session):
    """Счёт в статусе closed → AccountNotOpen."""
    user_id = uuid4()
    acc = _make_account(status="closed", client_id=user_id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result

    with pytest.raises(AccountNotOpen):
        await deposit(mock_session, user_id, acc.id, Decimal("100"), None)


@pytest.mark.asyncio
@patch("transaction_service.deposit.service.publish")
async def test_deposit_success(mock_publish, mock_session):
    """Успешное пополнение счёта."""
    user_id = uuid4()
    acc = _make_account(status="open", balance=Decimal("1000"), client_id=user_id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result
    mock_session.get.return_value = None  # контакт не найден

    tx = await deposit(mock_session, user_id, acc.id, Decimal("500"), "тест")

    assert acc.balance == Decimal("1500")
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited()


@pytest.mark.asyncio
@patch("transaction_service.deposit.service.publish")
async def test_deposit_frozen_allowed(mock_publish, mock_session):
    """Пополнение frozen-счёта допустимо."""
    user_id = uuid4()
    acc = _make_account(status="frozen", balance=Decimal("0"), client_id=user_id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result
    mock_session.get.return_value = None

    tx = await deposit(mock_session, user_id, acc.id, Decimal("100"), None)

    assert acc.balance == Decimal("100")


@pytest.mark.asyncio
@patch("transaction_service.deposit.service.publish")
async def test_deposit_integrity_error(mock_publish, mock_session):
    """IntegrityError при commit → TransactionConflict."""
    user_id = uuid4()
    acc = _make_account(status="open", balance=Decimal("1000"), client_id=user_id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_session.execute.return_value = mock_result
    mock_session.commit.side_effect = IntegrityError(None, None, Exception())

    with pytest.raises(TransactionConflict):
        await deposit(mock_session, user_id, acc.id, Decimal("100"), None)
    mock_session.rollback.assert_awaited()
