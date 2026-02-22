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

__all__ = ["POSTGRES_CORE_DATABASE_URL"]
