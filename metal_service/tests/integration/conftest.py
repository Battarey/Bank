import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from metal_service.main import app

INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "test-internal-key")

@pytest_asyncio.fixture
async def client(monkeypatch) -> AsyncGenerator[AsyncClient, None]:
	"""Фикстура для асинхронного клиента FastAPI."""
	
	# Сбросим кэш металлов перед каждым тестом
	import metal_service.metal_client as mc
	mc._cache.clear()
	
	# Мокаем Metals.Dev API (базовый URL)
	# Мы будем мокать _fetch_prices или httpx.AsyncClient в тестах
	
	async with AsyncClient(
		transport=ASGITransport(app=app),
		base_url="http://test",
		headers={"X-Internal-Key": INTERNAL_API_KEY}
	) as ac:
		yield ac
