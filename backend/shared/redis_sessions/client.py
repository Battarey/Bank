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


def get_client() -> Redis:
	"""Вернуть синглтон-клиент Redis для сессионных токенов из контейнера."""
	container = get_container()

	if container._redis_sessions is None:
		url = _resolve_redis_url()
		container._redis_sessions = Redis.from_url(url, encoding="utf-8", decode_responses=True)
	return container._redis_sessions


async def close_client() -> None:
	"""Закрыть пул соединений Redis через контейнер."""
	container = get_container()

	if container._redis_sessions:
		await container._redis_sessions.close()
		container._redis_sessions = None


async def ping() -> bool:
	"""Проверить доступность Redis."""
	try:
		client = get_client()
		return await client.ping()
	except Exception:
		return False


__all__ = ["close_client", "get_client", "ping"]
