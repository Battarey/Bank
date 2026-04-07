import pytest
from unittest.mock import patch, AsyncMock
from decimal import Decimal
from datetime import datetime, UTC

from metal_service.rates.service import get_all_prices
from metal_service.exceptions import RateUnavailable


@pytest.mark.asyncio
@patch("metal_service.rates.service.metal_client.get_metal_prices")
async def test_get_all_prices_success(mock_client):
    """Успешное получение цен через клиента."""
    prices = {"XAU": Decimal("6500.00"), "XAG": Decimal("85.50")}
    updated = datetime.now(UTC)
    mock_client.return_value = (prices, updated)

    res_prices, res_updated = await get_all_prices("RUB")

    assert res_prices == prices
    assert res_updated == updated
    mock_client.assert_awaited_once_with("RUB")


@pytest.mark.asyncio
@patch("metal_service.rates.service.metal_client.get_metal_prices")
async def test_get_all_prices_error(mock_client):
    """RateUnavailable — если клиент бросил ошибку."""
    mock_client.side_effect = Exception("Metals.Dev error")

    with pytest.raises(RateUnavailable, match="Не удалось получить цены металлов"):
        await get_all_prices("RUB")
