import os
import pytest
from unittest.mock import AsyncMock

if not os.getenv("RABBITMQ_HOST"):
	os.environ["RABBITMQ_HOST"] = "localhost"
if not os.getenv("DATABASE_URL"):
	os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
if not os.getenv("SECRET_KEY"):
	os.environ["SECRET_KEY"] = "test-secret"
if not os.getenv("INTERNAL_API_KEY"):
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
