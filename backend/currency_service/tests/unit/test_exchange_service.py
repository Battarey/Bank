import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from uuid import uuid4

from shared import models
from currency_service.exchange.service import exchange
from currency_service.exceptions import (
    SameAccountExchange, AccountNotFound, AccountNotOpen,
    SameCurrencyExchange, InsufficientFunds, RateUnavailable,
)


def _make_account(status="open", balance=Decimal("1000"), currency="RUB", client_id=None):
    acc = models.BankAccount()
    acc.id = uuid4()
    acc.client_id = client_id or uuid4()
    acc.status = status
    acc.balance = balance
    acc.currency = currency
    acc.account_number = "40817810000000000001"
    return acc


@pytest.mark.asyncio
async def test_exchange_same_account(mock_session):
    acc_id = uuid4()
    with pytest.raises(SameAccountExchange):
        await exchange(mock_session, uuid4(), acc_id, acc_id, Decimal("100"))


@pytest.mark.asyncio
async def test_exchange_from_not_found(mock_session):
    user_id = uuid4()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    with pytest.raises(AccountNotFound):
        await exchange(mock_session, user_id, uuid4(), uuid4(), Decimal("100"))


@pytest.mark.asyncio
async def test_exchange_same_currency(mock_session):
    user_id = uuid4()
    from_acc = _make_account(currency="RUB", client_id=user_id)
    to_acc = _make_account(currency="RUB", client_id=user_id)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [from_acc, to_acc]
    mock_session.execute.return_value = mock_result

    with pytest.raises(SameCurrencyExchange):
        await exchange(mock_session, user_id, from_acc.id, to_acc.id, Decimal("100"))


@pytest.mark.asyncio
async def test_exchange_insufficient_funds(mock_session):
    user_id = uuid4()
    from_acc = _make_account(currency="RUB", balance=Decimal("10"), client_id=user_id)
    to_acc = _make_account(currency="USD", client_id=user_id)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [from_acc, to_acc]
    mock_session.execute.return_value = mock_result

    with pytest.raises(InsufficientFunds):
        await exchange(mock_session, user_id, from_acc.id, to_acc.id, Decimal("100"))


@pytest.mark.asyncio
@patch("currency_service.exchange.service.exchange_client.get_fresh_rate")
@patch("currency_service.exchange.service.publish")
async def test_exchange_success(mock_publish, mock_rate, mock_session):
    mock_rate.return_value = (Decimal("0.011"), None)
    user_id = uuid4()
    from_acc = _make_account(currency="RUB", balance=Decimal("10000"), client_id=user_id)
    to_acc = _make_account(currency="USD", balance=Decimal("0"), client_id=user_id)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [from_acc, to_acc]
    mock_session.execute.return_value = mock_result
    mock_session.get.return_value = None  # нет контакта

    from_amount, to_amount, rate = await exchange(
        mock_session, user_id, from_acc.id, to_acc.id, Decimal("1000")
    )

    assert from_amount == Decimal("1000")
    assert to_amount == Decimal("11.00")  # 1000 * 0.011
    assert rate == Decimal("0.011")
    assert from_acc.balance == Decimal("9000")
    assert to_acc.balance == Decimal("11.00")


@pytest.mark.asyncio
@patch("currency_service.exchange.service.exchange_client.get_fresh_rate")
async def test_exchange_rate_unavailable(mock_rate, mock_session):
    mock_rate.side_effect = Exception("API timeout")
    user_id = uuid4()
    from_acc = _make_account(currency="RUB", balance=Decimal("1000"), client_id=user_id)
    to_acc = _make_account(currency="USD", balance=Decimal("0"), client_id=user_id)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [from_acc, to_acc]
    mock_session.execute.return_value = mock_result

    with pytest.raises(RateUnavailable):
        await exchange(mock_session, user_id, from_acc.id, to_acc.id, Decimal("100"))


@pytest.mark.asyncio
async def test_exchange_not_open(mock_session):
    user_id = uuid4()
    from_acc = _make_account(currency="RUB", status="closed", client_id=user_id)
    to_acc = _make_account(currency="USD", client_id=user_id)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [from_acc, to_acc]
    mock_session.execute.return_value = mock_result

    with pytest.raises(AccountNotOpen):
        await exchange(mock_session, user_id, from_acc.id, to_acc.id, Decimal("100"))
