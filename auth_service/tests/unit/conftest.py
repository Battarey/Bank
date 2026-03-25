import os
import pytest
from unittest.mock import AsyncMock

os.environ.setdefault("RABBITMQ_HOST", "localhost")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key")
os.environ.setdefault("ENCRYPTION_KEY", "MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE=")

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
