import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from shared.database_core.uow import AbstractUnitOfWork

# Set required environment variables
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/test")
os.environ.setdefault("REDIS_ONBOARDING_URL", "redis://localhost:6379/1")
os.environ.setdefault("EXCHANGE_NAME", "logs")
os.environ.setdefault("RABBITMQ_DSN", "amqp://guest:guest@localhost:5672/")


class FakeCustomerUnitOfWork(AbstractUnitOfWork):
    """Фейковый Unit of Work для тестирования Customer Service."""

    def __init__(self):
        super().__init__()
        self.customers = AsyncMock()        # mock CustomerRepository
        self.customer_queries = AsyncMock()  # mock CustomerQueryRepository
        self.committed = False
        self.rolled_back = False
        self.events = []

    def add_event(self, event):
        self.events.append(event)

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        return False


@pytest.fixture
def uow():
    """Фикстура для Unit of Work."""
    return FakeCustomerUnitOfWork()


@pytest.fixture
def mock_session():
    """Устаревшая фикстура для совместимости."""
    session = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.__aenter__.return_value = session
    return session


# Настройки для FastAPI/HTTPLX (если нужны для unit/интеграционных тестов)
from customer_service.main import app


@pytest_asyncio.fixture()
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
