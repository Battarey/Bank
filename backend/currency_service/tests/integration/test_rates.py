import pytest
from httpx import AsyncClient
from decimal import Decimal
from unittest.mock import AsyncMock
from datetime import datetime, UTC

@pytest.mark.asyncio
async def test_get_rates_success(client: AsyncClient, monkeypatch):
	"""Тест получения списка курсов."""
	from currency_service import exchange_client
	
	monkeypatch.setattr(exchange_client, "_fetch_rates", AsyncMock(return_value={
		"result": "success",
		"base_code": "RUB",
		"conversion_rates": {"USD": 0.01, "EUR": 0.009},
		"time_last_update_unix": int(datetime.now(UTC).timestamp())
	}))
	
	response = await client.get("/rates")
	assert response.status_code == 200
	data = response.json()
	assert data["base"] == "RUB"
	assert data["rates"]["USD"] == "0.01"
	assert data["rates"]["EUR"] == "0.009"

@pytest.mark.asyncio
async def test_get_pair_rate(client: AsyncClient, monkeypatch):
	"""Тест получения курса конкретной пары."""
	from currency_service import exchange_client
	
	monkeypatch.setattr(exchange_client, "_fetch_rates", AsyncMock(return_value={
		"result": "success",
		"base_code": "USD",
		"conversion_rates": {"RUB": 100.0},
		"time_last_update_unix": int(datetime.now(UTC).timestamp())
	}))
	
	response = await client.get("/rates/USD/RUB")
	assert response.status_code == 200
	assert response.json()["rate"] == "100.0"
@pytest.mark.asyncio
async def test_get_pair_rate_not_found(client: AsyncClient, monkeypatch):
	"""Тест запроса курса для несуществующей валюты."""
	from currency_service import exchange_client
	
	# API возвращает успех, но в списке нет нужной валюты
	monkeypatch.setattr(exchange_client, "_fetch_rates", AsyncMock(return_value={
		"result": "success",
		"base_code": "USD",
		"conversion_rates": {"EUR": 0.9},
		"time_last_update_unix": int(datetime.now(UTC).timestamp())
	}))
	
	response = await client.get("/rates/USD/INVALID")
	assert response.status_code == 404
	assert "не найдена" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_rates_external_api_failure(client: AsyncClient, monkeypatch):
	"""Тест обработки ошибки внешнего API."""
	from currency_service import exchange_client
	
	# Мокаем исключение при запросе к API
	monkeypatch.setattr(exchange_client, "_fetch_rates", AsyncMock(side_effect=RuntimeError("API Key Invalid")))
	
	response = await client.get("/rates/USD/RUB")
	assert response.status_code == 502
	assert "не удалось получить курс" in response.json()["detail"].lower()
