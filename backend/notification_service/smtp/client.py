"""Асинхронная отправка email через SMTP (Gmail / Yandex / другие)."""

import os
import ssl
from email.message import EmailMessage
from typing import Final

import aiosmtplib

SMTP_HOST: Final[str] = os.getenv("SMTP_HOST", "")
SMTP_PORT: Final[int] = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER: Final[str] = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: Final[str] = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM: Final[str] = os.getenv("SMTP_FROM", SMTP_USER)
SMTP_USE_TLS: Final[bool] = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")


async def send_email(to: str, subject: str, body: str) -> None:
	"""Отправить email через SMTP.

	Это низкоуровневый транспорт — тема и текст уже должны быть
	сформированы через шаблон (notification_service.templates).

	Raises RuntimeError если SMTP не сконфигурирован.
	"""

	if not SMTP_HOST or not SMTP_USER:
		raise RuntimeError("SMTP не сконфигурирован: задайте SMTP_HOST, SMTP_USER, SMTP_PASSWORD.")

	msg = EmailMessage()
	msg["From"] = SMTP_FROM
	msg["To"] = to
	msg["Subject"] = subject
	msg.set_content(body)

	tls_context = ssl.create_default_context() if SMTP_USE_TLS else None

	await aiosmtplib.send(
		msg,
		hostname=SMTP_HOST,
		port=SMTP_PORT,
		username=SMTP_USER,
		password=SMTP_PASSWORD,
		use_tls=SMTP_USE_TLS,
		tls_context=tls_context,
	)


__all__ = ["send_email"]
