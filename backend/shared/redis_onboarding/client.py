"""Асинхронный Redis-клиент для хранения черновиков онбординга."""

from redis.asyncio import Redis

from shared.bootstrap import get_container


def _resolve_redis_url() -> str:
	"""Определяет URL для Redis онбординга из Bootstrap-контейнера."""

	url = get_container().db_settings.REDIS_ONBOARDING_URL
	if not url:
		raise RuntimeError("REDIS_ONBOARDING_URL не задан в настройках!")
	return url


def get_client() -> Redis:
	"""Вернуть синглтон-клиент Redis для черновиков онбординга из контейнера."""
	container = get_container()

	if container._redis_onboarding is None:
		url = _resolve_redis_url()
		container._redis_onboarding = Redis.from_url(url, encoding="utf-8", decode_responses=True)
	return container._redis_onboarding


async def close_client() -> None:
	"""Закрыть пул соединений Redis через контейнер."""
	container = get_container()

	if container._redis_onboarding:
		await container._redis_onboarding.close()
		container._redis_onboarding = None


async def ping() -> bool:
	"""Проверить доступность Redis."""
	try:
		client = get_client()
		return await client.ping()
	except Exception:
		return False


__all__ = ["close_client", "get_client", "ping"]
