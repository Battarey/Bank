"""Помощники для хранения onboarding-токенов в Redis."""

import secrets
from datetime import timedelta
from uuid import UUID

from .client import get_client

DEFAULT_ONBOARDING_TTL = timedelta(minutes=15)


def generate_token() -> str:
	"""Генерирует случайный URL-safe onboarding-токен."""
	return secrets.token_urlsafe(32)


def _key(token: str) -> str:
	return f"onboarding:token:{token}"


async def save_onboarding_token(
	token: str,
	user_id: UUID,
	ttl: timedelta = DEFAULT_ONBOARDING_TTL,
) -> None:
	"""Сохранить отображение onboarding-token → user_id с TTL."""

	client = get_client()
	await client.set(_key(token), str(user_id), ex=int(ttl.total_seconds()))


async def load_onboarding_token(token: str) -> UUID | None:
	"""Получить user_id по onboarding-токену; None если истёк или не найден."""

	client = get_client()
	raw = await client.get(_key(token))
	return UUID(raw) if raw else None


async def touch_onboarding_token(
	token: str,
	ttl: timedelta = DEFAULT_ONBOARDING_TTL,
) -> None:
	"""Продлить TTL onboarding-токена (скользящая экспирация)."""

	client = get_client()
	await client.expire(_key(token), int(ttl.total_seconds()))


async def delete_onboarding_token(token: str) -> None:
	"""Удалить onboarding-токен (например, после finalize)."""

	client = get_client()
	await client.delete(_key(token))


__all__ = [
	"DEFAULT_ONBOARDING_TTL",
	"delete_onboarding_token",
	"generate_token",
	"load_onboarding_token",
	"save_onboarding_token",
	"touch_onboarding_token",
]
