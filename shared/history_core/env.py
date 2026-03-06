"""Переменные окружения для подключения к postgres_history."""

import os
from typing import Final


def _resolve_history_url() -> str:
	"""Возвращает URL-адрес БД истории."""

	value = os.getenv("HISTORY_DATABASE_URL")
	if value:
		return value

	raise RuntimeError(
		"HISTORY_DATABASE_URL не задан!"
	)


HISTORY_DATABASE_URL: Final[str] = _resolve_history_url()
