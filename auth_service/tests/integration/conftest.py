import os
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from auth_service.main import app
from shared.database_core.db import get_session
from shared.models import Base, User, Contact
from shared.redis_sessions import client as redis_client

# Используем тот же DATABASE_URL, что и сервис
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://test_user:test_password@postgres_test:5432/test_db")
REDIS_URL = os.environ.get("REDIS_SESSIONS_URL", "redis://redis_test:6379/0")

@pytest_asyncio.fixture(scope="function")
async def db_session():
	"""Создает новую базу данных для каждого теста и очищает ее."""
	engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
	async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)

	async with async_session_maker() as session:
		yield session

	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.drop_all)
	
	await engine.dispose()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clear_redis():
	"""Очищает Redis перед каждым тестом."""
	import redis.asyncio as redis
	r = redis.from_url(REDIS_URL)
	await r.flushdb()
	await r.aclose()
	yield
	await redis_client.close_client()


@pytest_asyncio.fixture(scope="function")
async def client(db_session, monkeypatch):
	"""Асинхронный клиент для тестирования FastAPI приложения."""
	
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
		headers={"X-Internal-Key": os.environ["INTERNAL_API_KEY"]}
	) as ac:
		yield ac
	
	app.dependency_overrides.clear()

@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession):
	"""Создает активного тестового пользователя."""
	from shared.models import User, Contact
	from shared.utils.security import get_blind_index
	from datetime import datetime
	
	user = User(
		id=uuid.uuid4(),
		created_at=datetime.utcnow(),
		updated_at=datetime.utcnow(),
		status="active",
		is_verified=True,
		pin_hash=None
	)
	
	contact = Contact(
		client_id=user.id,
		phone="+79991234567",
		phone_hash=get_blind_index("+79991234567"),
		email="test@example.com",
		email_hash=get_blind_index("test@example.com")
	)
	
	db_session.add(user)
	await db_session.flush()
	db_session.add(contact)
	await db_session.commit()
	return user
