"""Асинхронный Redis-клиент для хранения сессий и токенов."""

from redis.asyncio import Redis

from shared.bootstrap import get_container


def _resolve_redis_url() -> str:
	"""Определяет URL для сессионного Redis из Bootstrap-контейнера."""

	# Берем из типизированных настроек контейнера
	url = get_container().db_settings.REDIS_SESSIONS_URL
	if not url:
		raise RuntimeError("REDIS_SESSIONS_URL не задан в настройках!")
	return url


_client: Redis | None = None


def get_client() -> Redis:
	"""Вернуть синглтон-клиент Redis для сессионных токенов."""

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
