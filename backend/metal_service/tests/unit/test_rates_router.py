import pytest
from unittest.mock import patch, AsyncMock
from decimal import Decimal
from datetime import datetime, UTC
from fastapi import HTTPException

from metal_service.exceptions import RateUnavailable
from metal_service.rates.router import get_metal_rates


@pytest.mark.asyncio
@patch("metal_service.rates.router.service.get_all_prices")
async def test_get_metal_rates_success(mock_svc):
    """Роутер: успешное получение всех котировок металлов."""
    prices = {
        "XAU": Decimal("6500.00"),
        "XAG": Decimal("85.50"),
    }
    updated = datetime.now(UTC)
    mock_svc.return_value = (prices, updated)

    res = await get_metal_rates(base="RUB")

    assert res.base_currency == "RUB"
    assert len(res.rates) == 2
    assert res.last_updated == updated
    
    # Проверка структуры одного элемента
    gold_rate = next(r for r in res.rates if r.metal == "XAU")
    assert gold_rate.price_per_gram == Decimal("6500.00")


@pytest.mark.asyncio
@patch("metal_service.rates.router.service.get_all_prices")
async def test_get_metal_rates_empty(mock_svc):
    """Пустой ответ (нет металлов) — пустой список."""
    mock_svc.return_value = ({}, datetime.now(UTC))
    res = await get_metal_rates(base="USD")
    assert res.rates == []
    assert res.base_currency == "USD"


@pytest.mark.asyncio
@patch("metal_service.rates.router.service.get_all_prices")
async def test_get_metal_rates_unavailable(mock_svc):
    """502 Bad Gateway — при ошибке получения цен."""
    mock_svc.side_effect = RateUnavailable("Внешний API недоступен")

    with pytest.raises(HTTPException) as exc:
        await get_metal_rates(base="RUB")
    assert exc.value.status_code == 502
    assert "недоступен" in str(exc.value.detail)
