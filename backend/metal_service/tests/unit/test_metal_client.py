import pytest
import time
from unittest.mock import patch, AsyncMock, MagicMock
from decimal import Decimal
from datetime import datetime, timezone

from metal_service import metal_client


@pytest.fixture(autouse=True)
def reset_client_and_cache():
    """Сбрасывает глобальное состояние перед каждым тестом."""
    metal_client._client = None
    metal_client._cache.clear()
    yield
    metal_client._client = None
    metal_client._cache.clear()


# ── connect / disconnect ───────────────────────────────────────────────

@pytest.mark.asyncio
@patch("metal_service.metal_client.httpx.AsyncClient")
async def test_connect(mock_cls):
    mock_instance = MagicMock()
    mock_cls.return_value = mock_instance

    await metal_client.connect()
    assert metal_client._client == mock_instance


@pytest.mark.asyncio
@patch("metal_service.metal_client.httpx.AsyncClient")
async def test_disconnect(mock_cls):
    mock_instance = AsyncMock()
    mock_cls.return_value = mock_instance
    metal_client._client = mock_instance

    await metal_client.disconnect()

    mock_instance.aclose.assert_awaited_once()
    assert metal_client._client is None


@pytest.mark.asyncio
async def test_disconnect_no_client():
    """disconnect без connect не кидает ошибку."""
    await metal_client.disconnect()  # no error


# ── _fetch_prices ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_prices_no_client():
    with pytest.raises(RuntimeError, match="не инициализирован"):
        await metal_client._fetch_prices("RUB")


@pytest.mark.asyncio
async def test_fetch_prices_success():
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

    assert "XAU" in prices
    assert prices["XAU"] == Decimal("6500.00")
    assert prices["XAG"] == Decimal("85.50")
    assert isinstance(last_updated, datetime)


@pytest.mark.asyncio
async def test_fetch_prices_api_error():
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
async def test_fetch_prices_missing_metal():
    """Если металл отсутствует в ответе — он пропускается (не вызывает ошибки)."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "status": "success",
        "metals": {"gold": 6500.0},  # только золото
        "timestamp": "",
    }
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    metal_client._client = mock_client

    prices, _ = await metal_client._fetch_prices("RUB")

    assert "XAU" in prices
    assert "XAG" not in prices   # серебро отсутствовало


@pytest.mark.asyncio
async def test_fetch_prices_bad_timestamp():
    """Невалидный timestamp → datetime.now(utc) без ошибки."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "status": "success",
        "metals": {"gold": 6500.0},
        "timestamp": "NOT-A-DATE",
    }
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    metal_client._client = mock_client

    prices, last_updated = await metal_client._fetch_prices("RUB")
    assert isinstance(last_updated, datetime)


# ── get_metal_prices (кэш) ─────────────────────────────────────────────

@pytest.mark.asyncio
@patch("metal_service.metal_client._fetch_prices")
async def test_get_metal_prices_fetches_fresh(mock_fetch):
    prices = {"XAU": Decimal("6500.00")}
    updated = datetime.now(timezone.utc)
    mock_fetch.return_value = (prices, updated)

    result_prices, result_updated = await metal_client.get_metal_prices("RUB")

    assert result_prices == prices
    mock_fetch.assert_awaited_once_with("RUB")


@pytest.mark.asyncio
@patch("metal_service.metal_client._fetch_prices")
async def test_get_metal_prices_uses_cache(mock_fetch):
    """Второй вызов берёт данные из кэша без нового запроса."""
    prices = {"XAU": Decimal("6500.00")}
    updated = datetime.now(timezone.utc)
    mock_fetch.return_value = (prices, updated)

    await metal_client.get_metal_prices("RUB")
    await metal_client.get_metal_prices("RUB")

    assert mock_fetch.await_count == 1


@pytest.mark.asyncio
@patch("metal_service.metal_client.time")
@patch("metal_service.metal_client._fetch_prices")
async def test_get_metal_prices_cache_expired(mock_fetch, mock_time):
    """Просроченный кэш — новый запрос к API."""
    prices = {"XAU": Decimal("6500.00")}
    updated = datetime.now(timezone.utc)
    mock_fetch.return_value = (prices, updated)

    # Первый вызов — время = 0
    mock_time.monotonic.return_value = 0.0
    await metal_client.get_metal_prices("RUB")

    # Второй вызов — кэш истёк (TTL=30с, прошло 35с)
    mock_time.monotonic.return_value = 35.0
    await metal_client.get_metal_prices("RUB")

    assert mock_fetch.await_count == 2
