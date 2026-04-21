"""Асинхронный Redis-клиент для хранения черновиков онбординга."""

from redis.asyncio import Redis

from shared.bootstrap import get_container


def _resolve_redis_url() -> str:
	"""Определяет URL для Redis онбординга из Bootstrap-контейнера."""

	url = get_container().db_settings.REDIS_ONBOARDING_URL
	if not url:
		raise RuntimeError("REDIS_ONBOARDING_URL не задан в настройках!")
	return url


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
