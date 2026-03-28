import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _build_message(data: dict) -> MagicMock:
    """Создаёт мок aio_pika.IncomingMessage с заданным телом."""
    msg = MagicMock()
    msg.body = json.dumps(data).encode()
    # Мок context manager для message.process()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=None)
    ctx.__aexit__ = AsyncMock(return_value=False)
    msg.process.return_value = ctx
    return msg


@pytest.mark.asyncio
@patch("notification_service.main.save_notification")
@patch("notification_service.main.send_email")
@patch("notification_service.main.get_template")
async def test_process_message_success(mock_tmpl, mock_send, mock_save):
    """Корректное сообщение — шаблон рендерится, письмо отправлено, лог сохранён."""
    from notification_service.templates.templates import EmailTemplate
    fake_tmpl = MagicMock(spec=EmailTemplate)
    fake_tmpl.render.return_value = ("Тема", "Тело")
    mock_tmpl.return_value = fake_tmpl

    mock_send.return_value = None
    mock_save.return_value = None

    from notification_service.main import _process_message

    msg = _build_message({
        "type": "verification_code",
        "payload": {
            "to": "user@example.com",
            "variables": {"code": "123456"},
        },
    })

    await _process_message(msg)

    mock_tmpl.assert_called_once_with("verification_code")
    mock_send.assert_awaited_once_with(to="user@example.com", subject="Тема", body="Тело")
    mock_save.assert_awaited_once()
    call_kwargs = mock_save.call_args.kwargs
    assert call_kwargs["status"] == "sent"


@pytest.mark.asyncio
@patch("notification_service.main.save_notification")
@patch("notification_service.main.send_email")
async def test_process_message_invalid_json(mock_send, mock_save):
    """Невалидный JSON → silent drop, send_email не вызывается."""
    from notification_service.main import _process_message

    msg = MagicMock()
    msg.body = b"not-json!!!"
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=None)
    ctx.__aexit__ = AsyncMock(return_value=False)
    msg.process.return_value = ctx

    await _process_message(msg)

    mock_send.assert_not_awaited()
    mock_save.assert_not_awaited()


@pytest.mark.asyncio
@patch("notification_service.main.save_notification")
@patch("notification_service.main.send_email")
@patch("notification_service.main.get_template")
async def test_process_message_unknown_template(mock_tmpl, mock_send, mock_save):
    """Неизвестный тип → ValueError, send_email не вызывается."""
    mock_tmpl.side_effect = ValueError("unknown")
    from notification_service.main import _process_message

    msg = _build_message({
        "type": "unknown_type_xyz",
        "payload": {"to": "a@b.com", "variables": {}},
    })

    await _process_message(msg)

    mock_send.assert_not_awaited()
    mock_save.assert_not_awaited()


@pytest.mark.asyncio
@patch("notification_service.main.save_notification")
@patch("notification_service.main.send_email")
@patch("notification_service.main.get_template")
async def test_process_message_send_error_saves_failed(mock_tmpl, mock_send, mock_save):
    """Ошибка SMTP → save_notification вызывается со status='failed'."""
    from notification_service.templates.templates import EmailTemplate
    fake_tmpl = MagicMock(spec=EmailTemplate)
    fake_tmpl.render.return_value = ("Тема", "Тело")
    mock_tmpl.return_value = fake_tmpl
    mock_send.side_effect = Exception("SMTP error")
    mock_save.return_value = None

    from notification_service.main import _process_message

    msg = _build_message({
        "type": "welcome",
        "payload": {"to": "user@example.com", "variables": {}},
    })

    await _process_message(msg)

    mock_save.assert_awaited_once()
    assert mock_save.call_args.kwargs["status"] == "failed"
    assert "SMTP error" in mock_save.call_args.kwargs.get("error", "")
