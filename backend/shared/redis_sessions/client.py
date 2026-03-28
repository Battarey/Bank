"""Асинхронный Redis-клиент для хранения сессий и токенов."""

import os
from typing import Final
from redis.asyncio import Redis

REDIS_SESSIONS_URL: Final[str] = os.getenv("REDIS_SESSIONS_URL", "")

if not REDIS_SESSIONS_URL:
	import warnings
	warnings.warn(
		"REDIS_SESSIONS_URL is not set. Redis sessions client will fail at runtime.",
		stacklevel=2,
	)

_client: Redis | None = None


def get_client() -> Redis:
	"""Вернуть синглтон-клиент Redis для сессионных токенов."""

	global _client
	if _client is None:
		_client = Redis.from_url(REDIS_SESSIONS_URL, encoding="utf-8", decode_responses=True)
	return _client


async def close_client() -> None:
	"""Закрыть пул соединений Redis (например, при остановке сервиса)."""

	global _client
	if _client is None:
		return
	await _client.close()
	_client = None


__all__ = ["get_client", "close_client", "REDIS_SESSIONS_URL"]
