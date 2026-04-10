import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from log_service.consumers import _background_cleanup, _process_message, run_consumers
from log_service.schemas import LogEvent


@pytest.mark.asyncio
async def test_process_message_success(log_service):
    """Успешная обработка сообщения из RabbitMQ."""
    message = MagicMock()
    data = {
        "type": "login",
        "payload": {
            "user_id": str(uuid4()),
            "action": "login_success",
            "service": "auth_service"
        }
    }
    message.body = json.dumps(data).encode()
    
    # Mocking async with message.process()
    process_ctx = MagicMock()
    process_ctx.__aenter__ = AsyncMock(return_value=None)
    process_ctx.__aexit__ = AsyncMock(return_value=None)
    message.process.return_value = process_ctx
    
    with patch.object(log_service, "process_log", AsyncMock()) as mock_process:
        await _process_message(message, log_service)
        
        mock_process.assert_awaited_once()
        event = mock_process.call_args[0][0]
        assert isinstance(event, LogEvent)
        assert event.type == "login"


@pytest.mark.asyncio
async def test_process_message_invalid_json(log_service):
    """Ошибка при невалидном JSON в теле сообщения."""
    message = MagicMock()
    message.body = b"not-a-json"
    
    process_ctx = MagicMock()
    process_ctx.__aenter__ = AsyncMock(return_value=None)
    process_ctx.__aexit__ = AsyncMock(return_value=None)
    message.process.return_value = process_ctx
    
    with patch("log_service.consumers.logger") as mock_logger:
        await _process_message(message, log_service)
        mock_logger.error.assert_called_with("Невалидный JSON: %s", message.body[:200])


@pytest.mark.asyncio
async def test_background_cleanup(mock_postgres_repo):
    """Тест фоновой очистки логов."""
    # Чтобы цикл выполнился один раз и остановился на втором круге
    with patch("asyncio.sleep", side_effect=[None, Exception("Stop loop")]) as mock_sleep:
        with pytest.raises(Exception, match="Stop loop"):
            await _background_cleanup(mock_postgres_repo)
            
    # За этот цикл delete_old_history должен быть вызван 2 раза (перед каждым sleep)
    assert mock_postgres_repo.delete_old_history.await_count == 2


@pytest.mark.asyncio
@patch("log_service.consumers._init_history_db", AsyncMock())
@patch("log_service.consumers.init_clickhouse", AsyncMock())
@patch("log_service.consumers.close_clickhouse", AsyncMock())
@patch("log_service.consumers.aio_pika.connect_robust")
@patch("log_service.consumers.get_container")
@patch("asyncio.Event")
async def test_run_consumers_success(mock_event_cls, mock_container, mock_connect, mock_aio_pika):
    """Тест запуска потребителей (run_consumers)."""
    # Setup RabbitMQ mocks
    mock_connect.return_value = mock_aio_pika["connection"]
    
    # Setup settings
    mock_settings = MagicMock()
    mock_settings.RABBITMQ_URL = "amqp://test"
    mock_settings.LOGS_EXCHANGE = "logs"
    mock_settings.LOG_QUEUE = "queue"
    mock_settings.LOG_BINDING_KEY = "key"
    mock_container.return_value.settings = mock_settings
    
    # Setup stop event to break loop immediately
    mock_event = MagicMock()
    mock_event.wait = AsyncMock()
    mock_event_cls.return_value = mock_event
    
    async def empty_coro(*args, **kwargs):
        pass

    with patch("log_service.consumers.history_engine", AsyncMock()), \
         patch("log_service.consumers._background_cleanup", side_effect=empty_coro):
        await run_consumers()
        
    mock_connect.assert_awaited_once()
    mock_aio_pika["channel"].declare_exchange.assert_awaited_once()
    mock_aio_pika["queue"].consume.assert_called_once()
