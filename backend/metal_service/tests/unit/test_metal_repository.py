from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from metal_service.repositories.metal import MetalRepository


@pytest.fixture
def repository():
	return MetalRepository()


# ── connect / disconnect ───────────────────────────────────────────────


@pytest.mark.asyncio
@patch("metal_service.repositories.metal.httpx.AsyncClient")
async def test_connect(mock_cls, repository):
	"""Проверка создания клиента httpx."""
	mock_instance = MagicMock()
	mock_cls.return_value = mock_instance

	await repository.connect()
	assert repository._client == mock_instance


@pytest.mark.asyncio
@patch("metal_service.repositories.metal.httpx.AsyncClient")
async def test_disconnect(mock_cls, repository):
	"""Проверка закрытия клиента."""
	mock_instance = AsyncMock()
	mock_cls.return_value = mock_instance
	repository._client = mock_instance

	await repository.disconnect()

	mock_instance.aclose.assert_awaited_once()
	assert repository._client is None


# ── _fetch_from_api ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_from_api_success(repository):
	"""Успешное получение цен от внешнего API."""
	mock_resp = MagicMock()
	mock_resp.raise_for_status = MagicMock()
	mock_resp.json.return_value = {
		"status": "success",
		"metals": {
			"gold": 6500.0,
			"silver": 85.5,
		},
		"timestamp": "2026-01-01T12:00:00+00:00",
	}
	mock_client = AsyncMock()
	mock_client.get = AsyncMock(return_value=mock_resp)
	repository._client = mock_client

	prices, last_updated = await repository._fetch_from_api("RUB")

	assert prices["XAU"] == Decimal("6500.00")
	assert prices["XAG"] == Decimal("85.50")
	assert last_updated.year == 2026


# ── get_metal_prices (Кэширование и Lock) ──────────────────────────────


@pytest.mark.asyncio
@patch("metal_service.repositories.metal.MetalRepository._fetch_from_api")
async def test_get_metal_prices_use_cache(mock_fetch, repository):
	"""Проверка, что кэш работает."""
	prices = {"XAU": Decimal("100.00")}
	updated = datetime.now(UTC)
	mock_fetch.return_value = (prices, updated)

	# Первый вызов
	await repository.get_metal_prices("RUB")
	# Второй вызов
	await repository.get_metal_prices("RUB")

	assert mock_fetch.await_count == 1


@pytest.mark.asyncio
@patch("metal_service.repositories.metal.time")
@patch("metal_service.repositories.metal.MetalRepository._fetch_from_api")
async def test_get_metal_prices_cache_expired(mock_fetch, mock_time, repository):
	"""Проверка сброса кэша по TTL."""
	prices = {"XAU": Decimal("100.00")}
	updated = datetime.now(UTC)
	mock_fetch.return_value = (prices, updated)

	mock_time.monotonic.return_value = 0.0
	await repository.get_metal_prices("RUB")

	mock_time.monotonic.return_value = 100.0
	await repository.get_metal_prices("RUB")

	assert mock_fetch.await_count == 2
