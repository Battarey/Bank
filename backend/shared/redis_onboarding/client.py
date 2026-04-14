"""Асинхронный Redis-клиент для хранения черновиков онбординга."""

import os

from redis.asyncio import Redis


def _resolve_redis_url() -> str:
	"""Определяет URL для Redis онбординга из окружения или Bootstrap-контейнера."""
	try:
		from shared.bootstrap import get_container

		return get_container().db_settings.REDIS_ONBOARDING_URL or ""
	except (RuntimeError, ImportError):
		return os.getenv("REDIS_ONBOARDING_URL", "")


_client: Redis | None = None


def get_client() -> Redis:
	"""Вернуть синглтон-клиент Redis для черновиков онбординга."""

	global _client
	if _client is None:
		url = _resolve_redis_url()
		_client = Redis.from_url(url, encoding="utf-8", decode_responses=True)
	return _client


async def close_client() -> None:
	"""Закрыть пул соединений Redis (например, при остановке сервиса)."""

	global _client
	if _client is None:
		return
	await _client.close()
	_client = None


async def ping() -> bool:
	"""Проверить доступность Redis."""
	client = get_client()
	return await client.ping()


__all__ = ["close_client", "get_client", "ping"]
