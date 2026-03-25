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
from currency_service.main import app

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

@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
	async with session_factory() as session:
		yield session

@pytest_asyncio.fixture
async def client(db_session: AsyncSession, monkeypatch) -> AsyncGenerator[AsyncClient, None]:
	"""Фикстура для асинхронного клиента FastAPI."""
	
	async def _get_test_session():
		yield db_session

	app.dependency_overrides[get_session] = _get_test_session
	
	# Мокаем RabbitMQ
	import shared.rabbitmq.client as rmq
	from unittest.mock import AsyncMock
	monkeypatch.setattr(rmq, "publish", AsyncMock())
	
	# Сбросим кэш курсов
	import currency_service.exchange_client as ec
	ec._cache.clear()
	
	async with AsyncClient(
		transport=ASGITransport(app=app),
		base_url="http://test",
		headers={"X-Internal-Key": INTERNAL_API_KEY}
	) as ac:
		yield ac
	
	app.dependency_overrides.clear()
