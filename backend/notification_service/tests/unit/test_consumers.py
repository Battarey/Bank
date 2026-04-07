import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from notification_service.consumers import _process_message, run_consumers
from notification_service.schemas import NotificationTask


@pytest.mark.asyncio
async def test_process_message_success(notification_service):
    """Успешная обработка сообщения из RabbitMQ."""
    message = MagicMock()
    data = {
        "type": "verification_code",
        "payload": {
            "to": "test@example.com",
            "variables": {"code": "123456"}
        }
    }
    message.body = json.dumps(data).encode()
    
    # Mocking async with message.process()
    process_ctx = MagicMock()
    process_ctx.__aenter__ = AsyncMock(return_value=None)
    process_ctx.__aexit__ = AsyncMock(return_value=None)
    message.process.return_value = process_ctx
    
    with patch.object(notification_service, "process_notification", AsyncMock()) as mock_process:
        await _process_message(message, notification_service)
        
        mock_process.assert_awaited_once()
        task = mock_process.call_args[0][0]
        assert isinstance(task, NotificationTask)
        assert task.type == "verification_code"


@pytest.mark.asyncio
async def test_process_message_invalid_json(notification_service):
    """Ошибка при невалидном JSON в теле сообщения."""
    message = MagicMock()
    message.body = b"not-a-json"
    
    process_ctx = MagicMock()
    process_ctx.__aenter__ = AsyncMock(return_value=None)
    process_ctx.__aexit__ = AsyncMock(return_value=None)
    message.process.return_value = process_ctx
    
    with patch("notification_service.consumers.logger") as mock_logger:
        await _process_message(message, notification_service)
        mock_logger.error.assert_called_with("Невалидный JSON: %s", message.body[:200])


@pytest.mark.asyncio
@patch("notification_service.consumers.init_mongo", AsyncMock())
@patch("notification_service.consumers.close_mongo", AsyncMock())
@patch("notification_service.consumers.NotificationRepository")
@patch("notification_service.consumers.aio_pika.connect_robust")
@patch("notification_service.consumers.get_container")
@patch("asyncio.Event")
async def test_run_consumers_success(mock_event_cls, mock_container, mock_connect, mock_repo_cls, mock_aio_pika):
    """Тест запуска потребителей (run_consumers)."""
    # Setup RabbitMQ mocks
    mock_connect.return_value = mock_aio_pika["connection"]
    
    # Setup settings
    mock_settings = MagicMock()
    mock_settings.RABBITMQ_URL = "amqp://test"
    mock_settings.MONGO_URL = "mongodb://test"
    mock_settings.NOTIFICATIONS_EXCHANGE = "exchange"
    mock_settings.EMAIL_QUEUE = "queue"
    mock_settings.EMAIL_BINDING_KEY = "key"
    mock_container.return_value.settings = mock_settings
    
    # Setup stop event
    mock_event = MagicMock()
    mock_event.wait = AsyncMock()
    mock_event_cls.return_value = mock_event
    
    with patch("notification_service.consumers.asyncio.create_task", MagicMock()):
        await run_consumers()
        
    mock_connect.assert_awaited_once()
    mock_aio_pika["queue"].consume.assert_called_once()
