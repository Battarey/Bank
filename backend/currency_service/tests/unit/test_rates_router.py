import pytest
from unittest.mock import patch, AsyncMock
from decimal import Decimal
from datetime import datetime, timezone

from currency_service.exceptions import RateUnavailable, CurrencyNotAvailable
from currency_service.rates.router import get_rates, get_pair_rate


@pytest.mark.asyncio
@patch("currency_service.rates.router.service.get_all_rates")
async def test_get_rates_success(mock_svc):
    """Успешное получение списка курсов обмена через роутер."""
    rates = {"USD": Decimal("0.011"), "EUR": Decimal("0.010")}
    mock_svc.return_value = (rates, datetime.now(timezone.utc))

    res = await get_rates(base="RUB")
    assert res.base == "RUB"
    assert "USD" in res.rates
    assert res.rates["USD"] == Decimal("0.011")


@pytest.mark.asyncio
@patch("currency_service.rates.router.service.get_all_rates")
async def test_get_rates_error(mock_svc):
    """Ошибка (502) при недоступности внешнего API курсов."""
    from fastapi import HTTPException
    mock_svc.side_effect = RateUnavailable("timeout")
    with pytest.raises(HTTPException) as exc:
        await get_rates(base="RUB")
    assert exc.value.status_code == 502


@pytest.mark.asyncio
@patch("currency_service.rates.router.service.get_pair_rate")
async def test_get_pair_rate_success(mock_svc):
    """Успешное получение курса валютной пары через роутер."""
    mock_svc.return_value = (Decimal("0.011"), datetime.now(timezone.utc))
    res = await get_pair_rate(base="RUB", target="USD")
    assert res.rate == Decimal("0.011")
    assert res.base == "RUB"
    assert res.target == "USD"


@pytest.mark.asyncio
@patch("currency_service.rates.router.service.get_pair_rate")
async def test_get_pair_rate_not_found(mock_svc):
    """Ошибка (404) при запросе несуществующей валюты."""
    from fastapi import HTTPException
    mock_svc.side_effect = CurrencyNotAvailable("XYZ")
    with pytest.raises(HTTPException) as exc:
        await get_pair_rate(base="RUB", target="XYZ")
    assert exc.value.status_code == 404
