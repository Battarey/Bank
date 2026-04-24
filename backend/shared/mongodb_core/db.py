"""Модуль для работы с MongoDB.

Предоставляет асинхронный клиент motor для работы с MongoDB,
инструменты для инициализации, хелсчеков и управления индексами.
"""

from __future__ import annotations

import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger("shared.mongodb_core")

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def init_mongodb(
    mongo_url: str,
    db_name: str | None = None,
    indexes: list[dict[str, Any]] | None = None,
) -> None:
    """Инициализация подключения к MongoDB.

    Args:
        mongo_url: Строка подключения к MongoDB.
        db_name: Имя базы данных (если не указано в URL).
        indexes: Список описаний индексов для создания.
            Пример: [{"collection": "logs", "fields": [("created_at", 1)], "expireAfterSeconds": 3600}]
    """
    global _client, _db

    if _client is not None:
        logger.warning("MongoDB клиент уже инициализирован.")
        return

    _client = AsyncIOMotorClient(mongo_url)
    
    # Если имя базы не передано, берем дефолтную из URL
    if db_name:
        _db = _client[db_name]
    else:
        _db = _client.get_default_database()

    # Создание индексов, если они переданы
    if indexes and _db is not None:
        for idx in indexes:
            collection_name = idx["collection"]
            fields = idx["fields"]
            options = {k: v for k, v in idx.items() if k not in ("collection", "fields")}
            
            try:
                await _db[collection_name].create_index(fields, **options)
                logger.info("Индекс успешно создан для коллекции '%s'", collection_name)
            except Exception as exc:
                logger.error(
                    "Ошибка при создании индекса для коллекции '%s': %s",
                    collection_name,
                    exc,
                )

    logger.info("MongoDB успешно подключена: %s", _db.name if _db is not None else "Unknown")


async def close_mongodb() -> None:
    """Закрытие соединения с MongoDB."""
    global _client, _db

    if _client is not None:
        _client.close()
        _client = None
        _db = None
        logger.info("Соединение с MongoDB закрыто.")


async def ping_mongodb() -> bool:
    """Проверка доступности MongoDB.

    Returns:
        True, если база доступна, иначе False.
    """
    if _client is None:
        return False
    try:
        # Команда ping возвращает {'ok': 1.0}
        await _client.admin.command("ping")
        return True
    except Exception as exc:
        logger.error("Ошибка при выполнении Ping к MongoDB: %s", exc)
        return False


def get_mongodb() -> AsyncIOMotorDatabase:
    """Получение экземпляра базы данных.

    Returns:
        AsyncIOMotorDatabase: Асинхронный клиент БД.

    Raises:
        RuntimeError: Если MongoDB не была инициализирована.
    """
    if _db is None:
        raise RuntimeError(
            "MongoDB не инициализирована. Сначала вызовите init_mongodb()."
        )
    return _db
