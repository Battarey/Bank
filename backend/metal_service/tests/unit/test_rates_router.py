from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from metal_service.api.rates import get_metal_rates


@pytest.mark.asyncio
@patch("metal_service.services.rates.MetalRatesService.get_all_prices")
async def test_get_metal_rates_success(mock_svc_method):
	"""Роутер: успешное получение котировок."""
	prices = {"XAU": Decimal("6500.00")}
	updated = datetime.now(UTC)
	
	mock_service = AsyncMock()
	mock_service.get_all_prices.return_value = (prices, updated)
	
	res = await get_metal_rates(base="RUB", service=mock_service)

	assert res.base_currency == "RUB"
	assert res.rates[0].metal == "XAU"
	mock_service.get_all_prices.assert_awaited_once_with("RUB")
