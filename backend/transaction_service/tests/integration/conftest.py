import asyncio
import os
from datetime import UTC, datetime
from typing import AsyncGenerator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.database_core.db import get_session
from shared.models import Base
from transaction_service.main import app

# Используем URL из окружения (задается в docker-compose.test.yaml)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://test_user:test_password@postgres_test:5432/test_db")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "test-internal-key")

@pytest_asyncio.fixture()
async def engine_test():
	engine = create_async_engine(DATABASE_URL, echo=False)
	yield engine
	await engine.dispose()

@pytest_asyncio.fixture()
async def session_factory(engine_test):
	return async_sessionmaker(
		bind=engine_test, class_=AsyncSession, expire_on_commit=False
	)

@pytest_asyncio.fixture(autouse=True)
async def setup_db(engine_test):
	async with engine_test.begin() as conn:
		await conn.run_sync(Base.metadata.drop_all)
		await conn.run_sync(Base.metadata.create_all)
	yield
	async with engine_test.begin() as conn:
		await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
	async with session_factory() as session:
		yield session

@pytest_asyncio.fixture
async def client(db_session: AsyncSession, monkeypatch) -> AsyncGenerator[AsyncClient, None]:
	"""Фикстура для асинхронного клиента FastAPI с переопределенной БД и моками сервисов."""
	
	async def _get_test_session():
		yield db_session

	app.dependency_overrides[get_session] = _get_test_session
	
	# Мокаем RabbitMQ
	import shared.rabbitmq.client as rmq
	from unittest.mock import AsyncMock
	rmq._channel = AsyncMock()
	monkeypatch.setattr("shared.rabbitmq.client.publish", AsyncMock())
	
	# Мокаем Security Client (по умолчанию все разрешено)
	from transaction_service import security_client
	monkeypatch.setattr(security_client, "check_transaction", AsyncMock(return_value=(True, [])))
	
	# Мокаем Currency Client (курс 1:1 по умолчанию)
	from transaction_service import currency_client
	from decimal import Decimal
	monkeypatch.setattr(currency_client, "get_rate", AsyncMock(return_value=Decimal("1.0")))
	
	async with AsyncClient(
		transport=ASGITransport(app=app),
		base_url="http://test",
		headers={"X-Internal-Key": INTERNAL_API_KEY}
	) as ac:
		yield ac
	
	app.dependency_overrides.clear()
