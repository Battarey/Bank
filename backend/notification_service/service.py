"""Сервис для управления бизнес-логикой уведомлений."""

import logging
from typing import Any

from .repository import NotificationRepository
from .schemas import NotificationTask
from .smtp import send_email
from .templates import get_template

logger = logging.getLogger("notification_service")


class NotificationService:
	"""Сервис для обработки уведомлений."""

	def __init__(self, repository: NotificationRepository):
		self.repository = repository

	async def process_notification(self, task: NotificationTask) -> None:
		"""Обрабатывает одно задание на уведомление.
		
		1. Рендерит шаблон.
		2. Отправляет email.
		3. Сохраняет результат.
		"""
		msg_type = task.type
		payload = task.payload
		variables = payload.variables

		try:
			# 1. Рендеринг шаблона
			template = get_template(msg_type)
			subject, body, html_body = template.render(variables)

			# 2. Отправка Email
			await send_email(
				to=payload.to,
				subject=subject,
				body=body,
				html_body=html_body,
			)
			logger.info("%s → %s (HTML: %s)", msg_type, payload.to, bool(html_body))

			# 3. Успешное сохранение в журнал
			await self.repository.save(
				msg_type=msg_type,
				to=payload.to,
				subject=subject,
				body=body,
				variables=variables,
				status="sent",
			)

		except Exception as exc:
			logger.exception("Ошибка обработки уведомления type=%s", msg_type)
			
			# Фиксация ошибки в журнале
			await self.repository.save(
				msg_type=msg_type,
				to=str(payload.to),
				subject="",
				body="",
				variables=variables,
				status="failed",
				error=str(exc),
			)
