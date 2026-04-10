from unittest.mock import patch

import pytest

from notification_service.smtp.client import send_email


@pytest.mark.asyncio
@patch("notification_service.smtp.client.aiosmtplib.send")
async def test_send_email_success(mock_send, mock_bootstrap):
    """Успешная отправка email через aiosmtplib."""
    mock_send.return_value = None

    await send_email("user@example.com", "Тема", "Тело письма")

    mock_send.assert_awaited_once()
    # Проверка объекта сообщения (EmailMessage)
    msg = mock_send.call_args.args[0]
    assert msg["To"] == "user@example.com"
    assert msg["Subject"] == "Тема"
    assert "Тело письма" in msg.get_content()


@pytest.mark.asyncio
async def test_send_email_not_configured(mock_bootstrap):
    """Ошибка, если SMTP не сконфигурирован (пустой хост)."""
    mock_bootstrap.settings.SMTP_HOST = ""
    with pytest.raises(RuntimeError, match="SMTP не сконфигурирован"):
        await send_email("a@b.com", "s", "b")
