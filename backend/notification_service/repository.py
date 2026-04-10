"""Репозиторий для хранения уведомлений в MongoDB."""

import logging
from datetime import UTC, datetime
from typing import Any

from .store.client import COLLECTION_NAME, get_mongo

logger = logging.getLogger("notification_service")


class NotificationRepository:
	"""Репозиторий для работы с журналом уведомлений."""

	def __init__(self):
		self.db = get_mongo()
		self.collection = self.db[COLLECTION_NAME]

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
