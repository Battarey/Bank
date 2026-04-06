import pytest
from unittest.mock import AsyncMock

class FakeAccountUnitOfWork:
    """Универсальная имитация Unit of Work для всех тестов Account Service."""
    def __init__(self):
        self.accounts = AsyncMock()
        self.account_queries = AsyncMock()
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
    """Фикстура для Unit of Work (Fake для сервисов, Mock для роутеров)."""
    return FakeAccountUnitOfWork()

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.scalar = AsyncMock()
    session.execute = AsyncMock()
    return session
