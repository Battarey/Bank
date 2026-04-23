import time
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from currency_service.clients.exchange_client import ExchangeRateClient


@pytest.fixture
def client():
	"""Фикстура для создания свежего экземпляра клиента перед каждым тестом."""
	return ExchangeRateClient()


# ── connect / disconnect ────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("currency_service.clients.exchange_client.httpx.AsyncClient")
async def test_connect(mock_cls, client):
	mock_instance = MagicMock()
	mock_cls.return_value = mock_instance
	await client.connect()
	assert client._client == mock_instance


@pytest.mark.asyncio
@patch("currency_service.clients.exchange_client.httpx.AsyncClient")
async def test_disconnect(mock_cls, client):  # noqa: ARG001
	mock_instance = AsyncMock()
	client._client = mock_instance
	await client.disconnect()
	mock_instance.aclose.assert_awaited_once()
	assert client._client is None


@pytest.mark.asyncio
async def test_disconnect_no_client(client):
	await client.disconnect()  # no error


# ── _fetch_rates ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_rates_no_client(client):
	with pytest.raises(RuntimeError, match="не инициализирован"):
		await client._fetch_rates("RUB")


@pytest.mark.asyncio
async def test_fetch_rates_success(client):
	mock_resp = MagicMock()
	mock_resp.raise_for_status = MagicMock()
	mock_resp.json.return_value = {
		"result": "success",
		"conversion_rates": {"USD": 0.011, "EUR": 0.010},
		"time_last_update_unix": 1700000000,
	}
	mock_client = AsyncMock()
	mock_client.get = AsyncMock(return_value=mock_resp)
	client._client = mock_client

	data = await client._fetch_rates("RUB")
	assert data["result"] == "success"


@pytest.mark.asyncio
async def test_fetch_rates_api_error(client):
	mock_resp = MagicMock()
	mock_resp.raise_for_status = MagicMock()
	mock_resp.json.return_value = {"result": "error", "error-type": "invalid-key"}
	mock_client = AsyncMock()
	mock_client.get = AsyncMock(return_value=mock_resp)
	client._client = mock_client

	with pytest.raises(RuntimeError, match="invalid-key"):
		await client._fetch_rates("RUB")


# ── _parse_rates ────────────────────────────────────────────────────────


def test_parse_rates(client):
	data = {
		"conversion_rates": {"USD": 0.011, "EUR": 0.010},
		"time_last_update_unix": 1700000000,
	}
	rates, updated = client._parse_rates(data)
	assert "USD" in rates
	assert rates["USD"] == Decimal("0.011")
	assert isinstance(updated, datetime)


# ── get_rates (кэш) ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_rates_fetches(client):
	data = {
		"conversion_rates": {"USD": 0.011},
		"time_last_update_unix": 1700000000,
	}
	with patch.object(ExchangeRateClient, "_fetch_rates", return_value=data) as mock_fetch:
		rates, _updated = await client.get_rates("RUB")
		assert "USD" in rates
		mock_fetch.assert_awaited_once_with("RUB")


@pytest.mark.asyncio
async def test_get_rates_uses_cache(client):
	data = {"conversion_rates": {"USD": 0.011}, "time_last_update_unix": 1700000000}
	with patch.object(ExchangeRateClient, "_fetch_rates", return_value=data) as mock_fetch:
		await client.get_rates("RUB")
		await client.get_rates("RUB")
		assert mock_fetch.await_count == 1


@pytest.mark.asyncio
@patch("currency_service.clients.exchange_client.time")
async def test_get_rates_cache_expired(mock_time, client):
	data = {"conversion_rates": {"USD": 0.011}, "time_last_update_unix": 1700000000}
	with patch.object(ExchangeRateClient, "_fetch_rates", return_value=data) as mock_fetch:
		mock_time.monotonic.return_value = 0.0
		await client.get_rates("RUB")

		mock_time.monotonic.return_value = 1000.0  # Прошло много времени
		await client.get_rates("RUB")

		assert mock_fetch.await_count == 2


# ── get_fresh_rate ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_fresh_rate_from_cache(client):
	data = {"conversion_rates": {"USD": 0.011}, "time_last_update_unix": 1700000000}
	# Закладываем свежий кэш
	client._cache["RUB"] = (data, time.monotonic())
	
	with patch.object(ExchangeRateClient, "_fetch_rates") as mock_fetch:
		rate, _updated = await client.get_fresh_rate("RUB", "USD")
		assert rate == Decimal("0.011")
		mock_fetch.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_fresh_rate_currency_not_found(client):
	data = {"conversion_rates": {}, "time_last_update_unix": 1700000000}
	with patch.object(ExchangeRateClient, "_fetch_rates", return_value=data):
		with pytest.raises(ValueError, match="не найдена"):
			await client.get_fresh_rate("RUB", "XYZ")
