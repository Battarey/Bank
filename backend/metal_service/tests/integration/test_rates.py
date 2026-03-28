import pytest
from httpx import AsyncClient
from decimal import Decimal
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_get_metal_rates_success(client: AsyncClient, monkeypatch):
	"""Тест успешного получения курсов металлов."""
	# 1. Мокаем _fetch_prices в metal_client
	from metal_service import metal_client
	from datetime import datetime, UTC
	
	mock_prices = {
		"XAU": Decimal("7000.00"),
		"XAG": Decimal("90.00"),
		"XPT": Decimal("3500.00"),
		"XPD": Decimal("3300.00"),
	}
	mock_updated = datetime.now(UTC)
	
	monkeypatch.setattr(metal_client, "_fetch_prices", AsyncMock(return_value=(mock_prices, mock_updated)))
	
	# 2. Делаем запрос
	response = await client.get("/metals/rates")
	assert response.status_code == 200
	data = response.json()
	
	assert data["base_currency"] == "RUB"
	assert len(data["rates"]) == 4
	
	# Проверяем золото
	gold = next(r for r in data["rates"] if r["metal"] == "XAU")
	assert gold["price_per_gram"] == "7000.00"

@pytest.mark.asyncio
async def test_get_metal_rates_caching(client: AsyncClient, monkeypatch):
	"""Тест логики кэширования."""
	from metal_service import metal_client
	from datetime import datetime, UTC
	
	mock_prices = {"XAU": Decimal("7000.00")}
	mock_updated = datetime.now(UTC)
	
	mock_fetch = AsyncMock(return_value=(mock_prices, mock_updated))
	monkeypatch.setattr(metal_client, "_fetch_prices", mock_fetch)
	
	# Первый запрос - вызывает fetch
	await client.get("/metals/rates")
	assert mock_fetch.call_count == 1
	
	# Второй запрос - должен взять из кэша
	await client.get("/metals/rates")
	assert mock_fetch.call_count == 1

@pytest.mark.asyncio
async def test_get_metal_rates_different_base(client: AsyncClient, monkeypatch):
	"""Тест получения курсов в другой базовой валюте."""
	from metal_service import metal_client
	from datetime import datetime, UTC
	
	mock_fetch = AsyncMock(return_value=({"XAU": Decimal("80.50")}, datetime.now(UTC)))
	monkeypatch.setattr(metal_client, "_fetch_prices", mock_fetch)
	
	response = await client.get("/metals/rates?base=USD")
	assert response.status_code == 200
	data = response.json()
	assert data["base_currency"] == "USD"
	assert mock_fetch.call_args[0][0] == "USD"

@pytest.mark.asyncio
async def test_get_metal_rates_api_error(client: AsyncClient, monkeypatch):
	"""Тест обработки ошибки внешнего API."""
	from metal_service import metal_client
	
	# Имитируем ошибку
	monkeypatch.setattr(metal_client, "_fetch_prices", AsyncMock(side_effect=Exception("API Down")))
	
	response = await client.get("/metals/rates")
	assert response.status_code == 502
	assert "Не удалось получить цены металлов" in response.json()["detail"]
@pytest.mark.asyncio
async def test_get_rates_no_internal_key(client: AsyncClient):
	"""Попытка запроса без X-Internal-Key."""
	# Создаем новый клиент без заголовков фикстуры
	from metal_service.main import app
	from httpx import ASGITransport
	async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
		response = await ac.get("/metals/rates")
	assert response.status_code == 422 # Header(...) required by FastAPI


@pytest.mark.asyncio
async def test_get_rates_invalid_base_validation(client: AsyncClient):
	"""Проверка валидации параметра base (длина строки)."""
	# Слишком короткий
	response = await client.get("/metals/rates?base=RU")
	assert response.status_code == 422
	
	# Слишком длинный
	response = await client.get("/metals/rates?base=RUBLE")
	assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_rates_partial_data(client: AsyncClient, monkeypatch):
	"""Тест обработки частичных данных от API (один металл отсутствует)."""
	from metal_service import metal_client
	from datetime import datetime, UTC
	
	# API не возвращает серебро (XAG)
	mock_prices = {"XAU": Decimal("7000.00")} 
	monkeypatch.setattr(metal_client, "_fetch_prices", AsyncMock(return_value=(mock_prices, datetime.now(UTC))))
	
	response = await client.get("/metals/rates")
	assert response.status_code == 200
	data = response.json()
	assert len(data["rates"]) == 1
	assert data["rates"][0]["metal"] == "XAU"


@pytest.mark.asyncio
async def test_get_rates_external_api_logic_error(client: AsyncClient, monkeypatch):
	"""Тест обработки логической ошибки от внешнего API (status='error')."""
	from metal_service import metal_client
	
	# Мокаем _fetch_prices так, как если бы он выбросил ошибку из-за status="error" в JSON
	monkeypatch.setattr(metal_client, "_fetch_prices", AsyncMock(side_effect=RuntimeError("Metals.Dev API error 401: Invalid API Key")))
	
	response = await client.get("/metals/rates")
	assert response.status_code == 502
	assert "не удалось получить цены" in response.json()["detail"].lower()
