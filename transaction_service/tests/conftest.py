import os
import pytest
from unittest.mock import AsyncMock, MagicMock

os.environ["RABBITMQ_HOST"] = "localhost"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"
os.environ["CURRENCY_SERVICE_URL"] = "http://localhost:8001"
os.environ["SECURITY_SERVICE_URL"] = "http://localhost:8002"


@pytest.fixture
def mock_session():
    """Фикстура для имитации асинхронной сессии SQLAlchemy."""
    session = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    return session
