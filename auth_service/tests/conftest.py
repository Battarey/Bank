import os
import pytest
from unittest.mock import AsyncMock

os.environ["RABBITMQ_HOST"] = "localhost"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"

@pytest.fixture
def mock_session():
    """Фикстура для имитации асинхронной сессии SQLAlchemy."""
    session = AsyncMock()
    return session

@pytest.fixture
def mock_redis():
    """Фикстура для имитации Redis."""
    redis = AsyncMock()
    return redis
