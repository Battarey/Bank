import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from uuid import uuid4

from currency_service.exceptions import (
    AccountNotFound, AccountNotOpen, SameAccountExchange,
    InsufficientFunds, RateUnavailable, SameCurrencyExchange,
)
from currency_service.exchange.router import exchange_currency
from shared import schemas


def _make_payload():
    return schemas.ExchangeRequest.model_validate({
        "from_account_id": str(uuid4()),
        "to_account_id": str(uuid4()),
        "amount": "100.00",
    })


@pytest.mark.asyncio
@patch("currency_service.exchange.router.service.exchange")
async def test_exchange_router_success(mock_svc, mock_session):
    mock_svc.return_value = (Decimal("100"), Decimal("1.10"), Decimal("0.011"))

    from shared import models
    mock_from = models.BankAccount()
    mock_from.currency = "RUB"
    mock_to = models.BankAccount()
    mock_to.currency = "USD"
    mock_session.get.side_effect = [mock_from, mock_to]

    payload = _make_payload()
    res = await exchange_currency(payload=payload, user_id=uuid4(), session=mock_session)
    assert "Обмен выполнен" in res.message


@pytest.mark.asyncio
@patch("currency_service.exchange.router.service.exchange")
async def test_exchange_router_not_found(mock_svc, mock_session):
    from fastapi import HTTPException
    mock_svc.side_effect = AccountNotFound("нет")
    with pytest.raises(HTTPException) as exc:
        await exchange_currency(payload=_make_payload(), user_id=uuid4(), session=mock_session)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
@patch("currency_service.exchange.router.service.exchange")
async def test_exchange_router_same_account(mock_svc, mock_session):
    from fastapi import HTTPException
    mock_svc.side_effect = SameAccountExchange("тот же")
    with pytest.raises(HTTPException) as exc:
        await exchange_currency(payload=_make_payload(), user_id=uuid4(), session=mock_session)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
@patch("currency_service.exchange.router.service.exchange")
async def test_exchange_router_insufficient(mock_svc, mock_session):
    from fastapi import HTTPException
    mock_svc.side_effect = InsufficientFunds("мало")
    with pytest.raises(HTTPException) as exc:
        await exchange_currency(payload=_make_payload(), user_id=uuid4(), session=mock_session)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
@patch("currency_service.exchange.router.service.exchange")
async def test_exchange_router_rate_unavail(mock_svc, mock_session):
    from fastapi import HTTPException
    mock_svc.side_effect = RateUnavailable("нет курса")
    with pytest.raises(HTTPException) as exc:
        await exchange_currency(payload=_make_payload(), user_id=uuid4(), session=mock_session)
    assert exc.value.status_code == 502
