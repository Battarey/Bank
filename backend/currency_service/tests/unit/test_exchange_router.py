from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest

from currency_service.exchange.router import convert_currency
from shared import models, schemas


@pytest.fixture
def exchange_payload():
    return schemas.ExchangeRequest(
        from_account_id=uuid4(),
        to_account_id=uuid4(),
        amount=Decimal("1000")
    )

@pytest.mark.asyncio
@patch("currency_service.exchange.router.service.exchange")
async def test_convert_currency_success(mock_exchange, uow, exchange_payload):
    """Успешная конвертация валюты через роутер."""
    user_id = uuid4()
    mock_exchange.return_value = (Decimal("1000"), Decimal("11"), Decimal("0.011"))
    
    # Мокаем репозиторий для формирования ответа (линии 52-53 в router.py)
    uow.accounts.get_by_user.side_effect = [
        models.BankAccount(currency="RUB"),
        models.BankAccount(currency="USD")
    ]
    
    res = await convert_currency(payload=exchange_payload, user_id=user_id, uow=uow)
    
    assert res.message == "Конвертация успешно выполнена."
    assert res.from_amount == Decimal("1000")
    assert res.to_amount == Decimal("11")
    assert res.from_currency == "RUB"
    assert res.to_currency == "USD"
    
    mock_exchange.assert_awaited_once_with(
        uow, user_id, 
        from_account_id=exchange_payload.from_account_id,
        to_account_id=exchange_payload.to_account_id,
        amount=exchange_payload.amount
    )

@pytest.mark.asyncio
@patch("currency_service.exchange.router.service.exchange")
async def test_convert_currency_error(mock_exchange, uow, exchange_payload):
    """Ошибка при конвертации валюты через роутер."""
    from currency_service.exceptions import InsufficientFunds
    mock_exchange.side_effect = InsufficientFunds("Not enough funds")
    
    with pytest.raises(InsufficientFunds):
        await convert_currency(payload=exchange_payload, user_id=uuid4(), uow=uow)
