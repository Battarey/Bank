import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from log_service.service import LogService

# Устанавливаем переменные окружения
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
os.environ.setdefault("LOGS_EXCHANGE", "logs")
os.environ.setdefault("LOG_QUEUE", "log_queue")
os.environ.setdefault("LOG_BINDING_KEY", "log.#")

@pytest.fixture
def mock_postgres_repo():
    """Фикстура для мока PostgresHistoryRepository."""
    repo = AsyncMock()
    repo.save_action = AsyncMock()
    repo.delete_old_history = AsyncMock(return_value=10)
    return repo

@pytest.fixture
def mock_clickhouse_repo():
    """Фикстура для мока ClickHouseRepository."""
    repo = AsyncMock()
    repo.save_event = AsyncMock()
    return repo

@pytest.fixture
def log_service(mock_postgres_repo, mock_clickhouse_repo):
    """Фикстура LogService с мок-репозиториями."""
    return LogService(mock_postgres_repo, mock_clickhouse_repo)

@pytest.fixture
def mock_aio_pika():
    """Сложный мок для aio_pika."""
    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_exchange = AsyncMock()
    mock_queue = AsyncMock()
    
    mock_connection.channel.return_value = mock_channel
    mock_channel.declare_exchange.return_value = mock_exchange
    mock_channel.declare_queue.return_value = mock_queue
    
    # Чтобы поддерживать async with connection
    mock_connection.__aenter__.return_value = mock_connection
    mock_connection.__aexit__.return_value = None
    
    return {
        "connection": mock_connection,
        "channel": mock_channel,
        "exchange": mock_exchange,
        "queue": mock_queue,
    }
