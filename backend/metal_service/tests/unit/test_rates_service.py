from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from metal_service.services.rates import MetalRatesService
from shared.utils.exceptions import UnprocessableError


@pytest.fixture
def mock_repo():
	return MagicMock()


@pytest.fixture
def service(mock_repo):
	return MetalRatesService(repository=mock_repo)


@pytest.mark.asyncio
async def test_get_all_prices_success(service, mock_repo):
	"""Успешное получение цен через сервис."""
	prices = {"XAU": Decimal("6500.00")}
	updated = datetime.now(UTC)
	mock_repo.get_metal_prices = AsyncMock(return_value=(prices, updated))

	res_prices, res_updated = await service.get_all_prices("RUB")

	assert res_prices == prices
	assert res_updated == updated
	mock_repo.get_metal_prices.assert_awaited_once_with("RUB")


@pytest.mark.asyncio
async def test_get_all_prices_invalid_currency(service):
	"""Ошибка валидации при некорректной валюте."""
	with pytest.raises(UnprocessableError, match="Некорректный формат валюты"):
		await service.get_all_prices("INVALID")
