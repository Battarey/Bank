from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from transaction_service.currency_client import connect, disconnect, get_rate


@pytest.mark.asyncio
@patch("transaction_service.currency_client.httpx.AsyncClient")
async def test_get_rate_success(mock_client_cls, mock_bootstrap):  # noqa: ARG001
	"""Успешное получение курса валют."""
	mock_client = AsyncMock()
	mock_client_cls.return_value = mock_client

	# Mock response
	mock_res = MagicMock()
	mock_res.status_code = 200
	mock_res.json.return_value = {"rate": "92.50"}
	mock_client.get.return_value = mock_res

	# Инициализируем клиент
	await connect()

	rate = await get_rate("USD", "RUB")

	assert rate == Decimal("92.50")
	mock_client.get.assert_called_once()
	await disconnect()


@pytest.mark.asyncio
@patch("transaction_service.currency_client.httpx.AsyncClient")
async def test_get_rate_error(mock_client_cls, mock_bootstrap):  # noqa: ARG001
	"""Ошибка (напр. 500) от Currency Service."""
	mock_client = AsyncMock()
	mock_client_cls.return_value = mock_client

	mock_res = MagicMock(spec=httpx.Response)
	mock_res.status_code = 500
	mock_res.request = MagicMock(spec=httpx.Request)
	mock_res.raise_for_status.side_effect = httpx.HTTPStatusError(
		"500 error", request=mock_res.request, response=mock_res
	)
	mock_client.get.return_value = mock_res

	await connect()
	with pytest.raises(httpx.HTTPStatusError):
		await get_rate("USD", "RUB")
	await disconnect()
