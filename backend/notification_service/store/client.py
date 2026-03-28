"""Async MongoDB клиент для журнала уведомлений.

Хранит каждое отправленное (или неудавшееся) письмо как документ
с автоматическим TTL-удалением через 90 дней.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger("notification_service")

MONGO_URL: str = os.getenv("MONGO_URL", "mongodb://mongodb:27017/bank_notifications_db")
COLLECTION_NAME = "email_log"
TTL_DAYS = 90

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def init_mongo() -> None:
	"""Подключение к MongoDB и создание TTL-индекса."""

	global _client, _db  # noqa: PLW0603

	_client = AsyncIOMotorClient(MONGO_URL)
	_db = _client.get_default_database()

	# TTL-индекс: документы удаляются автоматически через 90 дней
	collection = _db[COLLECTION_NAME]
	await collection.create_index(
		"created_at",
		expireAfterSeconds=TTL_DAYS * 86_400,
	)

	logger.info("MongoDB подключена: %s", _db.name)


async def close_mongo() -> None:
	"""Закрытие соединения с MongoDB."""

	global _client, _db  # noqa: PLW0603

	if _client is not None:
		_client.close()
		_client = None
		_db = None
		logger.info("MongoDB отключена.")


def get_mongo() -> AsyncIOMotorDatabase:
	"""Получить экземпляр базы данных.

	Raises:
		RuntimeError: если init_mongo() не была вызвана.
	"""
	if _db is None:
		raise RuntimeError("MongoDB не инициализирована. Вызовите init_mongo().")
	return _db


async def save_notification(
	*,
	msg_type: str,
	to: str,
	subject: str,
	body: str,
	variables: dict[str, Any],
	status: str,
	error: str | None = None,
) -> None:
	"""Сохранить запись об уведомлении в журнал.

	Args:
		msg_type: Имя шаблона (например, ``verification_code``).
		to: Email получателя.
		subject: Тема письма (уже отрендеренная).
		body: Тело письма (уже отрендеренное).
		variables: Переменные, переданные в шаблон.
		status: ``"sent"`` или ``"failed"``.
		error: Текст ошибки (если ``status == "failed"``).
	"""

	db = get_mongo()

	doc = {
		"type": msg_type,
		"to": to,
		"subject": subject,
		"body": body,
		"variables": variables,
		"status": status,
		"error": error,
		"created_at": datetime.now(timezone.utc),
	}

	try:
		await db[COLLECTION_NAME].insert_one(doc)
	except Exception:
		logger.exception("Не удалось сохранить уведомление в MongoDB")
