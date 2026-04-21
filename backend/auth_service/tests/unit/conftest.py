import os
from unittest.mock import AsyncMock

import pytest

from shared.bootstrap.container import bootstrap
from shared.config.base import BaseAppSettings

os.environ.setdefault("RABBITMQ_HOST", "localhost")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key")
os.environ.setdefault("ENCRYPTION_KEY", "MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE=")


@pytest.fixture(scope="session", autouse=True)
def setup_test_container():
	"""Автоматическая инициализация контейнера настроек для всех тестов сессии."""
	bootstrap(BaseAppSettings)


@pytest.fixture
def mock_session():
	"""Фикстура для имитации асинхронной сессии SQLAlchemy."""
	session = AsyncMock()
	session.refresh = AsyncMock()
	session.commit = AsyncMock()
	session.rollback = AsyncMock()
	session.scalar = AsyncMock()
	session.execute = AsyncMock()
	return session


@pytest.fixture
def mock_redis():
	"""Фикстура для имитации Redis."""
	redis = AsyncMock()
	return redis


class FakeAuthUnitOfWork:
	"""Универсальная имитация Unit of Work для всех тестов Auth Service."""

	def __init__(self):
		self.users = AsyncMock()
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
	"""Фикстура для Unit of Work (Fake для сервисов)."""
	return FakeAuthUnitOfWork()
