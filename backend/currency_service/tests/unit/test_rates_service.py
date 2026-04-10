from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest

from currency_service.exceptions import CurrencyNotAvailable, RateUnavailable
from currency_service.rates.service import get_all_rates, get_pair_rate


@pytest.mark.asyncio
@patch("currency_service.rates.service.exchange_client.get_rates")
async def test_get_all_rates_success(mock_get):
    """Успешное получение всех курсов."""
    rates = {"USD": Decimal("0.011"), "EUR": Decimal("0.010")}
    updated = datetime.now(UTC)
    mock_get.return_value = (rates, updated)

    result_rates, result_updated = await get_all_rates("RUB")
    assert result_rates == rates
    assert result_updated == updated
    mock_get.assert_awaited_once_with("RUB")

@pytest.mark.asyncio
@patch("currency_service.rates.service.exchange_client.get_rates")
async def test_get_all_rates_error(mock_get):
    """Ошибка при получении всех курсов из внешнего API."""
    mock_get.side_effect = Exception("API timeout")
    with pytest.raises(RateUnavailable, match="Не удалось получить курсы"):
        await get_all_rates("RUB")

@pytest.mark.asyncio
@patch("currency_service.rates.service.exchange_client.get_rates")
async def test_get_pair_rate_success(mock_get):
    """Успешное получение курса конкретной пары."""
    rates = {"USD": Decimal("0.011"), "EUR": Decimal("0.010")}
    updated = datetime.now(UTC)
    mock_get.return_value = (rates, updated)

    rate, _ = await get_pair_rate("RUB", "USD")
    assert rate == Decimal("0.011")

@pytest.mark.asyncio
@patch("currency_service.rates.service.exchange_client.get_rates")
async def test_get_pair_rate_not_found(mock_get):
    """Ошибка: целевая валюта не поддерживается."""
    mock_get.return_value = ({"USD": Decimal("0.011")}, datetime.now(UTC))
    with pytest.raises(CurrencyNotAvailable):
        await get_pair_rate("RUB", "XYZ")

@pytest.mark.asyncio
@patch("currency_service.rates.service.exchange_client.get_rates")
async def test_get_pair_rate_api_error(mock_get):
    """Ошибка внешнего API при получении пары."""
    mock_get.side_effect = Exception("timeout")
    with pytest.raises(RateUnavailable):
        await get_pair_rate("RUB", "USD")
