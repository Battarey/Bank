import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from notification_service.service import NotificationService
from notification_service import repository

# Устанавливаем переменные окружения
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
os.environ.setdefault("NOTIFICATION_QUEUE", "notification_queue")
os.environ.setdefault("SMTP_HOST", "smtp.test")
os.environ.setdefault("SMTP_PORT", "465")
os.environ.setdefault("SMTP_USER", "user")
os.environ.setdefault("SMTP_PASSWORD", "pass")
os.environ.setdefault("SMTP_FROM", "from@test.com")

@pytest.fixture(autouse=True)
def mock_bootstrap():
    """Мокирует get_container для возврата настроек в тестах."""
    mock_settings = MagicMock()
    mock_settings.RABBITMQ_URL = "amqp://test"
    mock_settings.NOTIFICATION_QUEUE = "queue"
    mock_settings.SMTP_HOST = "smtp.test"
    mock_settings.SMTP_PORT = 465
    mock_settings.SMTP_USER = "user"
    mock_settings.SMTP_PASSWORD = "pass"
    mock_settings.smtp_from_addr = "from@test.com"
    mock_settings.SMTP_USE_TLS = True
    
    mock_container = MagicMock()
    mock_container.settings = mock_settings
    
    with patch("notification_service.smtp.client.get_container", return_value=mock_container), \
         patch("notification_service.consumers.get_container", return_value=mock_container):
        yield mock_container

@pytest.fixture
def mock_repo():
    """Фикстура для мока NotificationRepository."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    return repo

@pytest.fixture
def notification_service(mock_repo):
    """Фикстура NotificationService с мок-репозиторием."""
    return NotificationService(mock_repo)

@pytest.fixture
def mock_aio_pika():
    """Сложный мок для aio_pika."""
    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_queue = AsyncMock()
    
    mock_connection.channel.return_value = mock_channel
    mock_channel.declare_queue.return_value = mock_queue
    
    # Поддержка async with connection
    mock_connection.__aenter__.return_value = mock_connection
    mock_connection.__aexit__.return_value = None
    
    return {
        "connection": mock_connection,
        "channel": mock_channel,
        "queue": mock_queue,
    }
