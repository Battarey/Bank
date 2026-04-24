from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from metal_service.core.exceptions import RateUnavailable
from metal_service.api.rates import get_metal_rates


@pytest.mark.asyncio
@patch("metal_service.api.rates.service.get_all_prices")
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
@patch("metal_service.api.rates.service.get_all_prices")
async def test_get_metal_rates_empty(mock_svc):
	"""Пустой ответ (нет металлов) — пустой список."""
	mock_svc.return_value = ({}, datetime.now(UTC))
	res = await get_metal_rates(base="USD")
	assert res.rates == []
	assert res.base_currency == "USD"


@pytest.mark.asyncio
@patch("metal_service.api.rates.service.get_all_prices")
async def test_get_metal_rates_unavailable(mock_svc):
	"""Проверка, что исключение RateUnavailable пробрасывается наверх."""
	mock_svc.side_effect = RateUnavailable("Внешний API недоступен")

	with pytest.raises(RateUnavailable) as exc:
		await get_metal_rates(base="RUB")
	assert "недоступен" in str(exc.value)
