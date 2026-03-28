import pytest
from unittest.mock import patch, AsyncMock
from decimal import Decimal
from datetime import datetime, timezone

from metal_service.exceptions import RateUnavailable
from metal_service.rates.router import get_metal_rates


@pytest.mark.asyncio
@patch("metal_service.rates.router.service.get_all_prices")
async def test_get_metal_rates_success(mock_svc):
    prices = {
        "XAU": Decimal("6500.00"),
        "XAG": Decimal("85.50"),
        "XPT": Decimal("3200.00"),
        "XPD": Decimal("3100.00"),
    }
    updated = datetime.now(timezone.utc)
    mock_svc.return_value = (prices, updated)

    res = await get_metal_rates(base="RUB")

    assert res.base_currency == "RUB"
    assert len(res.rates) == 4
    assert res.last_updated == updated

    metals = {r.metal for r in res.rates}
    assert "XAU" in metals
    assert "XAG" in metals


@pytest.mark.asyncio
@patch("metal_service.rates.router.service.get_all_prices")
async def test_get_metal_rates_empty(mock_svc):
    """Пустой ответ (нет цен) → пустой список."""
    mock_svc.return_value = ({}, datetime.now(timezone.utc))
    res = await get_metal_rates(base="USD")
    assert res.rates == []
    assert res.base_currency == "USD"


@pytest.mark.asyncio
@patch("metal_service.rates.router.service.get_all_prices")
async def test_get_metal_rates_error(mock_svc):
    """RateUnavailable → 502 HTTPException."""
    from fastapi import HTTPException
    mock_svc.side_effect = RateUnavailable("API недоступен")

    with pytest.raises(HTTPException) as exc:
        await get_metal_rates(base="RUB")
    assert exc.value.status_code == 502
