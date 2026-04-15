"""Репозиторий для хранения уведомлений в MongoDB."""

import logging
from datetime import UTC, datetime
from typing import Any

from shared.mongodb_core import get_mongodb

logger = logging.getLogger("notification_service")


class NotificationRepository:
	"""Репозиторий для работы с журналом уведомлений."""

	def __init__(self):
		self.db = get_mongodb()
		self.collection = self.db["email_log"]

	async def save(
		self,
		*,
		msg_type: str,
		to: str,
		subject: str,
		body: str,
		variables: dict[str, Any],
		status: str,
		error: str | None = None,
	) -> None:
		"""Сохраняет запись об уведомлении в MongoDB."""

		doc = {
			"type": msg_type,
			"to": to,
			"subject": subject,
			"body": body,
			"variables": variables,
			"status": status,
			"error": error,
			"created_at": datetime.now(UTC),
		}

		try:
			await self.collection.insert_one(doc)
		except Exception:
			logger.exception("Не удалось сохранить уведомление в MongoDB")
