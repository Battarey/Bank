import os
from unittest.mock import AsyncMock, patch

# Set required environment variables before importing app
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@postgres_core:5432/bank_core")
os.environ.setdefault("REDIS_ONBOARDING_URL", "redis://redis_onboarding:6379/1")
os.environ.setdefault("EXCHANGE_NAME", "logs")
os.environ.setdefault("RABBITMQ_DSN", "amqp://guest:guest@rabbitmq:5672/")

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from customer_service.main import app
from shared.database_core.db import get_session
from shared.internal_auth import verify_internal_key

# Заглушка для аутентификации gateway
async def override_verify_internal_key():
    pass

app.dependency_overrides[verify_internal_key] = override_verify_internal_key

@pytest.fixture(scope="session", autouse=True)
def mock_external_services():
    with patch("customer_service.main.rmq_connect", new_callable=AsyncMock) as mock_connect, \
         patch("customer_service.main.rmq_disconnect", new_callable=AsyncMock) as mock_disconnect:
        yield

# Настройки для pytest-asyncio
@pytest.fixture(scope="session")
def event_loop():
    """Создает экземпляр event loop для всей тестовой сессии."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture()
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Асинхронный HTTP-клиент для вызовов FastAPI."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

