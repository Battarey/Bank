import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


# ── send_email ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("notification_service.smtp.client.aiosmtplib.send")
async def test_send_email_success(mock_send):
    """Успешная отправка email."""
    mock_send.return_value = None

    from notification_service.smtp.client import send_email
    await send_email("user@example.com", "Тема", "Тело письма")

    mock_send.assert_awaited_once()
    call_args = mock_send.call_args
    msg = call_args.args[0]
    assert msg["To"] == "user@example.com"
    assert msg["Subject"] == "Тема"


@pytest.mark.asyncio
async def test_send_email_not_configured():
    """При незаполненном SMTP_HOST кидает RuntimeError."""
    import importlib

    with patch.dict(os.environ, {"SMTP_HOST": "", "SMTP_USER": ""}):
        import notification_service.smtp.client as smtp_mod
        # Перебираем напрямую — симулируем незаполненный хост
        old_host = smtp_mod.SMTP_HOST
        old_user = smtp_mod.SMTP_USER
        smtp_mod.SMTP_HOST = ""
        smtp_mod.SMTP_USER = ""

        from notification_service.smtp.client import send_email
        with pytest.raises(RuntimeError, match="SMTP не сконфигурирован"):
            await send_email("a@b.com", "s", "b")

        smtp_mod.SMTP_HOST = old_host
        smtp_mod.SMTP_USER = old_user
