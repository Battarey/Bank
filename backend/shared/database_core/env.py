"""Переменные окружения для подключения к базе данных."""

import os
from typing import Final


def _resolve_database_url() -> str:
	"""Возвращает URL-адрес базы данных """

	for env_name in (
		"DATABASE_URL",
	):
		value = os.getenv(env_name)
		if value:
			return value

	raise RuntimeError(
		"DATABASE_URL не задан!"
	)

POSTGRES_CORE_DATABASE_URL: Final[str] = _resolve_database_url()

# Настройки пула соединений (Pool Tuning)
DB_POOL_SIZE: Final[int] = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW: Final[int] = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_RECYCLE: Final[int] = int(os.getenv("DB_POOL_RECYCLE", "1800"))

__all__ = [
	"POSTGRES_CORE_DATABASE_URL",
	"DB_POOL_SIZE",
	"DB_MAX_OVERFLOW",
	"DB_POOL_RECYCLE",
]
