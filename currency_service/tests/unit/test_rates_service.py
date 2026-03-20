import pytest
from unittest.mock import patch, AsyncMock
from decimal import Decimal
from datetime import datetime, timezone

from currency_service.exceptions import RateUnavailable, CurrencyNotAvailable
from currency_service.rates.service import get_all_rates, get_pair_rate


@pytest.mark.asyncio
@patch("currency_service.rates.service.exchange_client.get_rates")
async def test_get_all_rates_success(mock_get):
    rates = {"USD": Decimal("0.011"), "EUR": Decimal("0.010")}
    updated = datetime.now(timezone.utc)
    mock_get.return_value = (rates, updated)

    result_rates, result_updated = await get_all_rates("RUB")
    assert result_rates == rates
    mock_get.assert_awaited_once_with("RUB")


@pytest.mark.asyncio
@patch("currency_service.rates.service.exchange_client.get_rates")
async def test_get_all_rates_error(mock_get):
    mock_get.side_effect = Exception("API timeout")
    with pytest.raises(RateUnavailable, match="Не удалось получить курсы"):
        await get_all_rates("RUB")


@pytest.mark.asyncio
@patch("currency_service.rates.service.exchange_client.get_rates")
async def test_get_pair_rate_success(mock_get):
    rates = {"USD": Decimal("0.011"), "EUR": Decimal("0.010")}
    updated = datetime.now(timezone.utc)
    mock_get.return_value = (rates, updated)

    rate, _ = await get_pair_rate("RUB", "USD")
    assert rate == Decimal("0.011")


@pytest.mark.asyncio
@patch("currency_service.rates.service.exchange_client.get_rates")
async def test_get_pair_rate_not_found(mock_get):
    mock_get.return_value = ({"USD": Decimal("0.011")}, datetime.now(timezone.utc))
    with pytest.raises(CurrencyNotAvailable):
        await get_pair_rate("RUB", "XYZ")


@pytest.mark.asyncio
@patch("currency_service.rates.service.exchange_client.get_rates")
async def test_get_pair_rate_api_error(mock_get):
    mock_get.side_effect = Exception("timeout")
    with pytest.raises(RateUnavailable):
        await get_pair_rate("RUB", "USD")
