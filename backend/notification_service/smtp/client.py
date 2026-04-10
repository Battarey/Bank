"""Асинхронная отправка email через SMTP (Gmail / Yandex / другие)."""

import logging
from email.message import EmailMessage

import aiosmtplib

from shared.bootstrap import get_container

logger = logging.getLogger("notification_service.smtp")


async def send_email(to: str, subject: str, body: str, html_body: str | None = None) -> None:
	"""Отправить email через SMTP.

	Args:
		to: Email получателя.
		subject: Тема письма.
		body: Текстовая версия письма.
		html_body: HTML версия письма (необязательно).

	Raises:
		RuntimeError: Если SMTP не сконфигурирован.
	"""

	settings = get_container().settings
	if not settings.SMTP_HOST or not settings.SMTP_USER:
		raise RuntimeError("SMTP не сконфигурирован: задайте SMTP_HOST, SMTP_USER, SMTP_PASSWORD.")

	msg = EmailMessage()
	from email.utils import formataddr
	msg["From"] = formataddr(("Nexus Bank", settings.smtp_from_addr))
	msg["To"] = to
	msg["Subject"] = subject
	msg.set_content(body)

	if html_body:
		msg.add_alternative(html_body, subtype="html")

	try:
		logger.info(
			"Отправка email на %s через %s:%d (Implicit TLS: %s)...",
			to, settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USE_TLS
		)

		await aiosmtplib.send(
			msg,
			hostname=settings.SMTP_HOST,
			port=settings.SMTP_PORT,
			username=settings.SMTP_USER,
			password=settings.SMTP_PASSWORD,
			use_tls=settings.SMTP_USE_TLS,
		)
		logger.info("Email успешно отправлен.")

	except Exception as exc:
		logger.error("Ошибка при отправке email: %s", exc)
		raise


__all__ = ["send_email"]
