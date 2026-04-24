"""Модуль для работы с MongoDB.

Предоставляет асинхронный клиент motor для работы с MongoDB,
инструменты для инициализации, хелсчеков и управления индексами.
"""

from __future__ import annotations

import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger("shared.mongodb_core")

from shared.bootstrap import get_container

logger = logging.getLogger("shared.mongodb_core")


async def init_mongodb(
    mongo_url: str,
    db_name: str | None = None,
    indexes: list[dict[str, Any]] | None = None,
) -> None:
    """Инициализация подключения к MongoDB через контейнер."""
    container = get_container()

    if container._mongo_client is not None:
        logger.warning("MongoDB клиент уже инициализирован в контейнере.")
        return

    container._mongo_client = AsyncIOMotorClient(mongo_url)
    
    # Если имя базы не передано, берем дефолтную из URL
    if db_name:
        container._mongo_db = container._mongo_client[db_name]
    else:
        container._mongo_db = container._mongo_client.get_default_database()

    # Создание индексов, если они переданы
    if indexes and container._mongo_db is not None:
        for idx in indexes:
            collection_name = idx["collection"]
            fields = idx["fields"]
            options = {k: v for k, v in idx.items() if k not in ("collection", "fields")}
            
            try:
                await container._mongo_db[collection_name].create_index(fields, **options)
                logger.info("Индекс успешно создан для коллекции '%s'", collection_name)
            except Exception as exc:
                logger.error(
                    "Ошибка при создании индекса для коллекции '%s': %s",
                    collection_name,
                    exc,
                )

    db_name_str = container._mongo_db.name if container._mongo_db is not None else "Unknown"
    logger.info("MongoDB успешно подключена: %s", db_name_str)


async def close_mongodb() -> None:
    """Закрытие соединения с MongoDB через контейнер."""
    container = get_container()

    if container._mongo_client is not None:
        container._mongo_client.close()
        container._mongo_client = None
        container._mongo_db = None
        logger.info("Соединение с MongoDB закрыто.")


async def ping_mongodb() -> bool:
    """Проверка доступности MongoDB через контейнер."""
    container = get_container()
    client = container._mongo_client

    if client is None:
        return False
    try:
        await client.admin.command("ping")
        return True
    except Exception as exc:
        logger.error("Ошибка при выполнении Ping к MongoDB: %s", exc)
        return False


def get_mongodb() -> AsyncIOMotorDatabase:
    """Получение экземпляра базы данных из контейнера."""
    container = get_container()
    db = container._mongo_db

    if db is None:
        raise RuntimeError(
            "MongoDB не инициализирована в контейнере. Сначала вызовите init_mongodb()."
        )
    return db
