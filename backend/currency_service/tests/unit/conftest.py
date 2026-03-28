import os
import pytest
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("EXCHANGE_RATE_API_KEY", "test-key")
os.environ.setdefault("EXCHANGE_RATE_BASE_URL", "https://v6.exchangerate-api.com/v6")
os.environ.setdefault("EXCHANGE_RATE_CACHE_TTL", "30")
os.environ.setdefault("EXCHANGE_RATE_TRADE_TTL", "60")
os.environ.setdefault("RABBITMQ_HOST", "localhost")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key")


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    return session
