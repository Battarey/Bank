import os
import pytest
from unittest.mock import AsyncMock

os.environ.setdefault("RABBITMQ_HOST", "localhost")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017/test_security_db")
os.environ["SECRET_KEY"] = "test-secret"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"

@pytest.fixture
def mock_session():
    """Фикстура для имитации асинхронной сессии SQLAlchemy."""
    session = AsyncMock()
    return session

@pytest.fixture
def mock_mongo():
    """Фикстура для имитации MongoDB."""
    mongo = AsyncMock()
    return mongo
