import os
import pytest
from unittest.mock import AsyncMock, MagicMock

# Устанавливаем переменные окружения ДО любых импортов кода приложения
os.environ["RABBITMQ_URL"] = "amqp://guest:guest@localhost:5672/"
os.environ["HISTORY_DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_history"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test" 
os.environ["CLICKHOUSE_HOST"] = "localhost"
os.environ["CLICKHOUSE_PORT"] = "8123"
os.environ["CLICKHOUSE_USER"] = "default"
os.environ["CLICKHOUSE_PASSWORD"] = ""
os.environ["CLICKHOUSE_DB"] = "default"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"

@pytest.fixture
def mock_history_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session
