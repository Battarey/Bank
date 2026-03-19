import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal

from transaction_service import currency_client


@pytest.fixture(autouse=True)
def reset_client():
    currency_client._client = None
    yield
    currency_client._client = None


@pytest.mark.asyncio
async def test_connect_disconnect():
    with patch("transaction_service.currency_client.httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value = mock_instance

        await currency_client.connect()
        assert currency_client._client == mock_instance

        await currency_client.disconnect()
        mock_instance.aclose.assert_awaited_once()
        assert currency_client._client is None


@pytest.mark.asyncio
async def test_get_rate_not_initialized():
    with pytest.raises(RuntimeError, match="не инициализирован"):
        await currency_client.get_rate("RUB", "USD")


@pytest.mark.asyncio
async def test_get_rate_success():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"rate": "0.012"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    currency_client._client = mock_client

    rate = await currency_client.get_rate("RUB", "USD")
    assert rate == Decimal("0.012")
    mock_client.get.assert_awaited_once_with(
        "/rates/RUB/USD",
        headers={"X-Internal-Key": "test-internal-key"},
    )
