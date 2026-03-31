"""Асинхронная отправка email через SMTP (Gmail / Yandex / другие)."""

import os
import ssl
from email.message import EmailMessage
from typing import Final

import aiosmtplib

from ..config import settings


async def send_email(to: str, subject: str, body: str) -> None:
	"""Отправить email через SMTP.

	Args:
		to: Email получателя.
		subject: Тема письма.
		body: Текст письма.

	Raises:
		RuntimeError: Если SMTP не сконфигурирован.
	"""

	if not settings.SMTP_HOST or not settings.SMTP_USER:
		raise RuntimeError("SMTP не сконфигурирован: задайте SMTP_HOST, SMTP_USER, SMTP_PASSWORD.")

	msg = EmailMessage()
	msg["From"] = settings.smtp_from_addr
	msg["To"] = to
	msg["Subject"] = subject
	msg.set_content(body)

	tls_context = ssl.create_default_context() if settings.SMTP_USE_TLS else None

	await aiosmtplib.send(
		msg,
		hostname=settings.SMTP_HOST,
		port=settings.SMTP_PORT,
		username=settings.SMTP_USER,
		password=settings.SMTP_PASSWORD,
		use_tls=settings.SMTP_USE_TLS,
		tls_context=tls_context,
	)


__all__ = ["send_email"]
