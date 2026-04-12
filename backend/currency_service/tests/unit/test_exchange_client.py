import time
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from currency_service import exchange_client


@pytest.fixture(autouse=True)
def reset_state():
	exchange_client._client = None
	exchange_client._cache.clear()
	yield
	exchange_client._client = None
	exchange_client._cache.clear()


# ── connect / disconnect ────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("currency_service.exchange_client.httpx.AsyncClient")
async def test_connect(mock_cls):
	mock_instance = MagicMock()
	mock_cls.return_value = mock_instance
	await exchange_client.connect()
	assert exchange_client._client == mock_instance


@pytest.mark.asyncio
@patch("currency_service.exchange_client.httpx.AsyncClient")
async def test_disconnect(mock_cls):  # noqa: ARG001
	mock_instance = AsyncMock()
	exchange_client._client = mock_instance
	await exchange_client.disconnect()
	mock_instance.aclose.assert_awaited_once()
	assert exchange_client._client is None


@pytest.mark.asyncio
async def test_disconnect_no_client():
	await exchange_client.disconnect()  # no error


# ── _fetch_rates ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_rates_no_client():
	with pytest.raises(RuntimeError, match="не инициализирован"):
		await exchange_client._fetch_rates("RUB")


@pytest.mark.asyncio
async def test_fetch_rates_success():
	mock_resp = MagicMock()
	mock_resp.raise_for_status = MagicMock()
	mock_resp.json.return_value = {
		"result": "success",
		"conversion_rates": {"USD": 0.011, "EUR": 0.010},
		"time_last_update_unix": 1700000000,
	}
	mock_client = AsyncMock()
	mock_client.get = AsyncMock(return_value=mock_resp)
	exchange_client._client = mock_client

	data = await exchange_client._fetch_rates("RUB")
	assert data["result"] == "success"


@pytest.mark.asyncio
async def test_fetch_rates_api_error():
	mock_resp = MagicMock()
	mock_resp.raise_for_status = MagicMock()
	mock_resp.json.return_value = {"result": "error", "error-type": "invalid-key"}
	mock_client = AsyncMock()
	mock_client.get = AsyncMock(return_value=mock_resp)
	exchange_client._client = mock_client

	with pytest.raises(RuntimeError, match="invalid-key"):
		await exchange_client._fetch_rates("RUB")


# ── _parse_rates ────────────────────────────────────────────────────────


def test_parse_rates():
	data = {
		"conversion_rates": {"USD": 0.011, "EUR": 0.010},
		"time_last_update_unix": 1700000000,
	}
	rates, updated = exchange_client._parse_rates(data)
	assert "USD" in rates
	assert rates["USD"] == Decimal("0.011")
	assert isinstance(updated, datetime)


# ── get_rates (кэш) ─────────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("currency_service.exchange_client._fetch_rates")
async def test_get_rates_fetches(mock_fetch):
	data = {
		"conversion_rates": {"USD": 0.011},
		"time_last_update_unix": 1700000000,
	}
	mock_fetch.return_value = data

	rates, _updated = await exchange_client.get_rates("RUB")
	assert "USD" in rates
	mock_fetch.assert_awaited_once_with("RUB")


@pytest.mark.asyncio
@patch("currency_service.exchange_client._fetch_rates")
async def test_get_rates_uses_cache(mock_fetch):
	data = {"conversion_rates": {"USD": 0.011}, "time_last_update_unix": 1700000000}
	mock_fetch.return_value = data

	await exchange_client.get_rates("RUB")
	await exchange_client.get_rates("RUB")

	assert mock_fetch.await_count == 1


@pytest.mark.asyncio
@patch("currency_service.exchange_client.time")
@patch("currency_service.exchange_client._fetch_rates")
async def test_get_rates_cache_expired(mock_fetch, mock_time):
	data = {"conversion_rates": {"USD": 0.011}, "time_last_update_unix": 1700000000}
	mock_fetch.return_value = data

	mock_time.monotonic.return_value = 0.0
	await exchange_client.get_rates("RUB")

	mock_time.monotonic.return_value = 35.0
	await exchange_client.get_rates("RUB")

	assert mock_fetch.await_count == 2


# ── get_fresh_rate ──────────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("currency_service.exchange_client._fetch_rates")
async def test_get_fresh_rate_from_cache(mock_fetch):
	data = {"conversion_rates": {"USD": 0.011}, "time_last_update_unix": 1700000000}
	# Закладываем свежий кэш
	exchange_client._cache["RUB"] = (data, time.monotonic())
	mock_fetch.return_value = data

	rate, _updated = await exchange_client.get_fresh_rate("RUB", "USD")
	assert rate == Decimal("0.011")
	mock_fetch.assert_not_awaited()


@pytest.mark.asyncio
@patch("currency_service.exchange_client._fetch_rates")
async def test_get_fresh_rate_currency_not_found(mock_fetch):
	data = {"conversion_rates": {}, "time_last_update_unix": 1700000000}
	mock_fetch.return_value = data

	with pytest.raises(ValueError, match="не найдена"):
		await exchange_client.get_fresh_rate("RUB", "XYZ")
