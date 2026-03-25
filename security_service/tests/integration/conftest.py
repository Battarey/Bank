import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from security_service.main import app
from shared.database_core.db import get_session
from shared.models import Base
from security_service.store.client import init_mongo, close_mongo, _get_db, COLLECTION_NAME

# Форсируем использование тестовых контейнеров
DATABASE_URL = os.getenv(
	"DATABASE_URL",
	"postgresql+asyncpg://test_user:test_password@postgres_test:5432/test_db"
)
os.environ["DATABASE_URL"] = DATABASE_URL
os.environ["MONGO_URL"] = os.getenv("MONGO_URL", "mongodb://mongodb_test:27017/test_security_db")

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
		
	# Инициализация MongoDB
	await init_mongo()
	
	yield
	
	await close_mongo()
	async with engine_test.begin() as conn:
		await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(session_factory):
	"""Фикстура, предоставляющая сессию БД на один тест."""
	async with session_factory() as session:
		yield session

@pytest_asyncio.fixture(scope="function", autouse=True)
async def clear_mongo():
	"""Очищаем коллекцию MongoDB перед каждым тестом."""
	try:
		db = _get_db()
		await db[COLLECTION_NAME].delete_many({})
		yield
	except Exception:
		yield

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
