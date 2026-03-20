import pytest
from unittest.mock import patch, AsyncMock
from decimal import Decimal
from datetime import datetime, timezone

from metal_service.exceptions import RateUnavailable
from metal_service.rates.service import get_all_prices


@pytest.mark.asyncio
@patch("metal_service.rates.service.metal_client.get_metal_prices")
async def test_get_all_prices_success(mock_get):
    prices = {"XAU": Decimal("6500.00"), "XAG": Decimal("85.50")}
    updated = datetime.now(timezone.utc)
    mock_get.return_value = (prices, updated)

    result_prices, result_updated = await get_all_prices("RUB")

    assert result_prices == prices
    assert result_updated == updated
    mock_get.assert_awaited_once_with("RUB")


@pytest.mark.asyncio
@patch("metal_service.rates.service.metal_client.get_metal_prices")
async def test_get_all_prices_error_raises_rate_unavailable(mock_get):
    mock_get.side_effect = Exception("API timeout")

    with pytest.raises(RateUnavailable, match="Не удалось получить цены металлов"):
        await get_all_prices("USD")
