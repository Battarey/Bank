"""Асинхронный Redis-клиент для хранения черновиков онбординга."""

import os
from typing import Final
from redis.asyncio import Redis


REDIS_ONBOARDING_URL: Final[str] = os.getenv("REDIS_ONBOARDING_URL")

_client: Redis | None = None


def get_client() -> Redis:
	"""Вернуть синглтон-клиент Redis для черновиков онбординга."""

	global _client
	if _client is None:
		_client = Redis.from_url(REDIS_ONBOARDING_URL, encoding="utf-8", decode_responses=True)
	return _client


async def close_client() -> None:
	"""Закрыть пул соединений Redis (например, при остановке сервиса)."""

	global _client
	if _client is None:
		return
	await _client.close()
	_client = None


__all__ = ["get_client", "close_client", "REDIS_ONBOARDING_URL"]
