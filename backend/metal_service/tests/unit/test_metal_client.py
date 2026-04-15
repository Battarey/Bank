from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from metal_service.clients import metal_client

# Фикстура сброса в conftest.py работает превосходно


# ── connect / disconnect ───────────────────────────────────────────────


@pytest.mark.asyncio
@patch("metal_service.clients.metal_client.httpx.AsyncClient")
async def test_connect(mock_cls):
	"""Проверка создания клиента httpx."""
	mock_instance = MagicMock()
	mock_cls.return_value = mock_instance

	await metal_client.connect()
	assert metal_client._client == mock_instance


@pytest.mark.asyncio
@patch("metal_service.clients.metal_client.httpx.AsyncClient")
async def test_disconnect(mock_cls):
	"""Проверка закрытия клиента."""
	mock_instance = AsyncMock()
	mock_cls.return_value = mock_instance
	metal_client._client = mock_instance

	await metal_client.disconnect()

	mock_instance.aclose.assert_awaited_once()
	assert metal_client._client is None


@pytest.mark.asyncio
async def test_disconnect_no_client():
	"""disconnect без предварительного connect не должен вызывать ошибок."""
	await metal_client.disconnect()  # No error should occur


# ── _fetch_prices ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_prices_no_client():
	"""Ошибка, если клиент не инициализирован."""
	with pytest.raises(RuntimeError, match="не инициализирован"):
		await metal_client._fetch_prices("RUB")


@pytest.mark.asyncio
async def test_fetch_prices_success():
	"""Успешное получение цен от внешнего API."""
	mock_resp = MagicMock()
	mock_resp.raise_for_status = MagicMock()
	mock_resp.json.return_value = {
		"status": "success",
		"metals": {
			"gold": 6500.0,
			"silver": 85.5,
			"platinum": 3200.0,
			"palladium": 3100.0,
		},
		"timestamp": "2026-01-01T12:00:00+00:00",
	}
	mock_client = AsyncMock()
	mock_client.get = AsyncMock(return_value=mock_resp)
	metal_client._client = mock_client

	prices, last_updated = await metal_client._fetch_prices("RUB")

	assert prices["XAU"] == Decimal("6500.00")
	assert prices["XAG"] == Decimal("85.50")
	assert prices["XPT"] == Decimal("3200.00")
	assert prices["XPD"] == Decimal("3100.00")
	assert last_updated.year == 2026
	assert last_updated.month == 1


@pytest.mark.asyncio
async def test_fetch_prices_api_error():
	"""Обработка ошибки статуса (error) в JSON ответе."""
	mock_resp = MagicMock()
	mock_resp.raise_for_status = MagicMock()
	mock_resp.json.return_value = {
		"status": "error",
		"error_code": "INVALID_KEY",
		"error_message": "Invalid API key",
	}
	mock_client = AsyncMock()
	mock_client.get = AsyncMock(return_value=mock_resp)
	metal_client._client = mock_client

	with pytest.raises(RuntimeError, match="INVALID_KEY"):
		await metal_client._fetch_prices("RUB")


@pytest.mark.asyncio
async def test_fetch_prices_bad_timestamp():
	"""Некорректный timestamp в ответе не должен ронять парсинг."""
	mock_resp = MagicMock()
	mock_resp.raise_for_status = MagicMock()
	mock_resp.json.return_value = {
		"status": "success",
		"metals": {"gold": 100.0},
		"timestamp": "INVALID",
	}
	mock_client = AsyncMock()
	mock_client.get = AsyncMock(return_value=mock_resp)
	metal_client._client = mock_client

	_, last_updated = await metal_client._fetch_prices("RUB")
	assert isinstance(last_updated, datetime)


# ── get_metal_prices (Кэширование) ─────────────────────────────────────


@pytest.mark.asyncio
@patch("metal_service.clients.metal_client._fetch_prices")
async def test_get_metal_prices_use_cache(mock_fetch):
	"""Проверка, что кэш работает и не делает лишних запросов."""
	prices = {"XAU": Decimal("100.00")}
	updated = datetime.now(UTC)
	mock_fetch.return_value = (prices, updated)

	# Первый вызов
	await metal_client.get_metal_prices("RUB")
	# Второй вызов
	await metal_client.get_metal_prices("RUB")

	assert mock_fetch.await_count == 1


@pytest.mark.asyncio
@patch("metal_service.clients.metal_client.time")
@patch("metal_service.clients.metal_client._fetch_prices")
async def test_get_metal_prices_cache_expired(mock_fetch, mock_time):
	"""Проверка сброса кэша по TTL."""
	prices = {"XAU": Decimal("100.00")}
	updated = datetime.now(UTC)
	mock_fetch.return_value = (prices, updated)

	# Время 0
	mock_time.monotonic.return_value = 0.0
	await metal_client.get_metal_prices("RUB")

	# Прошло 100 секунд (TTL 30)
	mock_time.monotonic.return_value = 100.0
	await metal_client.get_metal_prices("RUB")

	assert mock_fetch.await_count == 2
