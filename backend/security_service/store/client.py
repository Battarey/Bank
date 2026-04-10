"""Async MongoDB клиент для журнала событий безопасности.

Хранит каждое срабатывание AML-правила как документ
с автоматическим TTL-удалением через 365 дней.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from shared.bootstrap import get_container

from ..config import SecuritySettings

logger = logging.getLogger("security_service")

def _get_settings() -> SecuritySettings:
	"""Получает специфические настройки для сервиса безопасности."""
	return get_container().settings


_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def init_mongo() -> None:
	"""Подключение к MongoDB и создание TTL-индекса."""

	global _client, _db  # noqa: PLW0603

	settings = _get_settings()
	_client = AsyncIOMotorClient(settings.MONGO_URL)
	_db = _client.get_default_database()

	collection = _db[settings.SECURITY_COLLECTION]
	await collection.create_index(
		"created_at",
		expireAfterSeconds=settings.SECURITY_TTL_DAYS * 86_400,
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


def _get_db() -> AsyncIOMotorDatabase:
	"""Получить экземпляр базы данных."""
	if _db is None:
		raise RuntimeError("MongoDB не инициализирована. Вызовите init_mongo().")
	return _db


async def save_event(
	*,
	account_id: str,
	rule: str,
	details: dict[str, Any],
	action: str,
	threshold: str | None = None,
	actual: str | None = None,
) -> None:
	"""Сохранить событие безопасности (срабатывание AML-правила).

	Args:
		account_id: UUID счёта (строка).
		rule: Имя сработавшего правила.
		details: Подробности (суммы, количества и т.д.).
		action: Предпринятое действие (freeze, reject).
		threshold: Пороговое значение правила.
		actual: Фактическое значение, вызвавшее срабатывание.
	"""

	db = _get_db()
	settings = _get_settings()
	doc = {
		"account_id": account_id,
		"rule": rule,
		"details": details,
		"action": action,
		"threshold": threshold,
		"actual": actual,
		"created_at": datetime.now(UTC),
	}
	await db[settings.SECURITY_COLLECTION].insert_one(doc)
	logger.info("Security event: rule=%s, account=%s, action=%s", rule, account_id, action)
