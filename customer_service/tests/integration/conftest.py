import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from customer_service.main import app
from shared.database_core.db import get_session
from shared.models import Base

# Используем URL из окружения (задается в docker-compose.test.yaml)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://test_user:test_password@postgres_test:5432/test_db")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "test-internal-key")

@pytest_asyncio.fixture()
async def engine_test():
	engine = create_async_engine(DATABASE_URL, future=True)
	yield engine
	await engine.dispose()

@pytest_asyncio.fixture()
async def session_factory(engine_test):
	return async_sessionmaker(
		bind=engine_test,
		autoflush=False,
		expire_on_commit=False,
	)

@pytest_asyncio.fixture(autouse=True)
async def setup_database(engine_test):
	"""Создает таблицы перед началом теста и удаляет их после."""
	async with engine_test.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)
	yield
	async with engine_test.begin() as conn:
		await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(autouse=True)
async def clear_redis():
	"""Очищает Redis перед каждым тестом."""
	from shared.redis_onboarding.client import get_client
	client = get_client()
	try:
		# Пытаемся очистить только нужную БД (она задана в URL)
		await client.flushdb()
	except Exception as e:
		print(f"Warning: Failed to flush Redis: {e}")
	yield

@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
	"""Фикстура для сессии БД."""
	async with session_factory() as session:
		yield session

@pytest_asyncio.fixture
async def client(db_session: AsyncSession, monkeypatch) -> AsyncGenerator[AsyncClient, None]:
	"""Фикстура для асинхронного клиента FastAPI с переопределенной БД и замоканным RabbitMQ."""
	
	async def _get_test_session():
		yield db_session

	app.dependency_overrides[get_session] = _get_test_session
	
	# Мокаем RabbitMQ
	import shared.rabbitmq.client as rmq
	from unittest.mock import AsyncMock
	rmq._channel = AsyncMock()
	
	async with AsyncClient(
		transport=ASGITransport(app=app),
		base_url="http://test",
		headers={"X-Internal-Key": INTERNAL_API_KEY}
	) as ac:
		yield ac
	
	app.dependency_overrides.clear()
