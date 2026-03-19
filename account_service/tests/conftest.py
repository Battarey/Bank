import os
import pytest
from unittest.mock import AsyncMock

os.environ["RABBITMQ_HOST"] = "localhost"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.scalar = AsyncMock()
    session.execute = AsyncMock()
    return session
