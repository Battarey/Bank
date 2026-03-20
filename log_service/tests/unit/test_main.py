import json
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from log_service.main import (
    _save_to_history, 
    _save_to_clickhouse, 
    _process_message,
    _init_history_db,
    run,
    main
)

# ── _init_history_db ───────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("log_service.main.history_engine")
async def test_init_history_db(mock_engine):
    mock_conn = AsyncMock()
    mock_engine.begin.return_value.__aenter__.return_value = mock_conn
    
    await _init_history_db()
    
    mock_conn.run_sync.assert_called_once()


# ── _save_to_history ───────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("log_service.main.HistorySessionLocal")
async def test_save_to_history_success(mock_session_cls):
    mock_session = AsyncMock()
    mock_session.add = MagicMock()  # SQLAlchemy add не асинхронный
    mock_session_cls.return_value.__aenter__.return_value = mock_session
    
    user_id = uuid4()
    entity_id = uuid4()
    data = {
        "type": "transaction",
        "payload": {
            "user_id": str(user_id),
            "entity_id": str(entity_id),
            "action": "deposit",
            "service": "transaction_service",
            "details": "Test deposit",
            "entity_type": "transaction",
            "amount": "100.00",
            "currency": "RUB",
            "status": "success",
            "ip_address": "127.0.0.1"
        }
    }
    
    await _save_to_history(data)
    
    mock_session.add.assert_called_once()
    action = mock_session.add.call_args.args[0]
    assert action.user_id == user_id
    assert action.entity_id == entity_id
    assert action.action == "deposit"
    assert action.status == "success"
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_to_history_no_user_id():
    with patch("log_service.main.HistorySessionLocal") as mock_session_cls:
        await _save_to_history({"payload": {}})
        mock_session_cls.assert_not_called()


@pytest.mark.asyncio
async def test_save_to_history_invalid_user_id():
    with patch("log_service.main.HistorySessionLocal") as mock_session_cls:
        await _save_to_history({"payload": {"user_id": "not-a-uuid"}})
        mock_session_cls.assert_not_called()


# ── _save_to_clickhouse ────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("log_service.main.insert_log_event")
async def test_save_to_clickhouse_success(mock_insert):
    data = {
        "type": "login",
        "payload": {
            "user_id": str(uuid4()),
            "action": "login_success",
            "service": "auth_service"
        }
    }
    
    await _save_to_clickhouse(data)
    
    mock_insert.assert_awaited_once()
    kwargs = mock_insert.call_args.kwargs
    assert kwargs["event_type"] == "login"
    assert kwargs["service"] == "auth_service"


# ── _process_message ───────────────────────────────────────────────────

def _build_message(data: dict) -> MagicMock:
    msg = MagicMock()
    msg.body = json.dumps(data).encode()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=None)
    ctx.__aexit__ = AsyncMock(return_value=False)
    msg.process.return_value = ctx
    return msg


@pytest.mark.asyncio
@patch("log_service.main._save_to_history")
@patch("log_service.main._save_to_clickhouse")
async def test_process_message_success(mock_ch, mock_hist):
    msg = _build_message({"type": "test", "payload": {}})
    await _process_message(msg)
    
    mock_hist.assert_awaited_once()
    mock_ch.assert_awaited_once()


@pytest.mark.asyncio
@patch("log_service.main.logger")
async def test_process_message_invalid_json(mock_logger):
    msg = MagicMock()
    msg.body = b"invalid"
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=None)
    ctx.__aexit__ = AsyncMock(return_value=False)
    msg.process.return_value = ctx
    
    await _process_message(msg)
    mock_logger.error.assert_called()


@pytest.mark.asyncio
@patch("log_service.main._save_to_history")
@patch("log_service.main._save_to_clickhouse")
@patch("log_service.main.logger")
async def test_process_message_gather_errors(mock_logger, mock_ch, mock_hist):
    """Проверяем, что ошибки в gather логируются, но не прерывают выполнение."""
    mock_hist.side_effect = Exception("Hist error")
    mock_ch.side_effect = Exception("CH error")
    
    msg = _build_message({"type": "test", "payload": {}})
    await _process_message(msg)
    
    # Должно быть два вызова logger.exception
    assert mock_logger.exception.call_count == 2


# ── run ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("log_service.main._init_history_db")
@patch("log_service.main.init_clickhouse")
@patch("log_service.main.aio_pika.connect_robust")
@patch("log_service.main.asyncio.Event")
async def test_run_success(mock_event, mock_connect, mock_ch, mock_hist):
    # Мокаем RabbitMQ
    mock_conn = AsyncMock()
    mock_connect.return_value = mock_conn
    mock_channel = AsyncMock()
    mock_conn.channel.return_value = mock_channel
    
    # Мокаем событие остановки, чтобы оно сразу сработало
    mock_event_instance = MagicMock()
    mock_event_instance.wait = AsyncMock()
    mock_event.return_value = mock_event_instance
    
    mock_history_engine = AsyncMock()
    
    with patch("log_service.main.close_clickhouse"), \
         patch("log_service.main.history_engine", mock_history_engine):
        await run()
    
    mock_hist.assert_awaited_once()
    mock_ch.assert_awaited_once()
    mock_connect.assert_awaited_once()
    mock_channel.declare_exchange.assert_awaited_once()
    mock_channel.declare_queue.assert_awaited_once()
    mock_history_engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
@patch("log_service.main._init_history_db", AsyncMock())
@patch("log_service.main.init_clickhouse", AsyncMock())
@patch("log_service.main.close_clickhouse", AsyncMock())
@patch("log_service.main.history_engine", AsyncMock())
@patch("log_service.main.aio_pika.connect_robust")
@patch("log_service.main.asyncio.sleep", AsyncMock())
@patch("log_service.main.asyncio.Event")
async def test_run_rabbitmq_retry_success(mock_event, mock_connect):
    """Проверяем, что run() делает ретраи при ошибке подключения к RabbitMQ."""
    # Первая попытка - ошибка, вторая - успех
    mock_conn = AsyncMock()
    mock_connect.side_effect = [Exception("Conn error"), mock_conn]
    
    # Мокаем событие остановки
    mock_event_instance = MagicMock()
    mock_event_instance.wait = AsyncMock()
    mock_event.return_value = mock_event_instance
    
    await run()
    
    assert mock_connect.call_count == 2


@pytest.mark.asyncio
@patch("log_service.main._init_history_db", AsyncMock())
@patch("log_service.main.init_clickhouse", AsyncMock())
@patch("log_service.main.close_clickhouse", AsyncMock())
@patch("log_service.main.history_engine", AsyncMock())
@patch("log_service.main.aio_pika.connect_robust")
@patch("log_service.main.asyncio.get_running_loop")
@patch("log_service.main.asyncio.Event")
async def test_run_signal_handling(mock_event, mock_loop_get, mock_connect):
    """Проверяем установку обработчиков сигналов."""
    mock_connect.return_value = AsyncMock()
    mock_loop = MagicMock()
    mock_loop_get.return_value = mock_loop
    
    # Чтобы выйти из run()
    mock_event_instance = MagicMock()
    mock_event_instance.wait = AsyncMock()
    mock_event.return_value = mock_event_instance
    
    await run()
    
    # Должно быть 2 вызова add_signal_handler (SIGINT, SIGTERM)
    assert mock_loop.add_signal_handler.call_count >= 1
    
    # Проверяем сам обработчик (signal_handler)
    callback = mock_loop.add_signal_handler.call_args.args[1]
    callback()
    mock_event_instance.set.assert_called_once()


# ── main entrypoint ────────────────────────────────────────────────────

@patch("log_service.main.asyncio.run")
def test_main_entrypoint(mock_run):
    main()
    mock_run.assert_called_once()
