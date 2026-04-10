import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.database_core.uow import AbstractUnitOfWork

# Установка переменных окружения для тестов
os.environ.setdefault("EXCHANGE_RATE_API_KEY", "test-key")
os.environ.setdefault("EXCHANGE_RATE_BASE_URL", "https://v6.exchangerate-api.com/v6")
os.environ.setdefault("EXCHANGE_RATE_CACHE_TTL", "30")
os.environ.setdefault("EXCHANGE_RATE_TRADE_TTL", "60")
os.environ.setdefault("RABBITMQ_HOST", "localhost")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key")


class FakeCurrencyUnitOfWork(AbstractUnitOfWork):
    """Фейковый Unit of Work для тестирования Currency Service (в стиле Account Service)."""

    def __init__(self):
        super().__init__()
        self.accounts = AsyncMock()    # mock CurrencyRepository
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
    return FakeCurrencyUnitOfWork()


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
    
    # Поддержка контекстного менеджера
    session.__aenter__.return_value = session
    return session
