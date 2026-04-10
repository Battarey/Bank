"""Async MongoDB клиент для журнала уведомлений.

Хранит каждое отправленное (или неудавшееся) письмо как документ
с автоматическим TTL-удалением через 90 дней.
"""

from __future__ import annotations

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger("notification_service")

# MongoDB
COLLECTION_NAME = "email_log"
TTL_DAYS = 90

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def init_mongo(mongo_url: str) -> None:
	"""Подключение к MongoDB и создание TTL-индекса."""

	global _client, _db  # noqa: PLW0603

	_client = AsyncIOMotorClient(mongo_url)
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
