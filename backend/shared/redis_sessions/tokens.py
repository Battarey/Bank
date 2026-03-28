"""Высокоуровневые помощники для хранения пользовательских сессионных токенов в Redis."""

from datetime import timedelta
from typing import Any
from uuid import UUID
from .client import get_client

DEFAULT_SESSION_TTL = timedelta(minutes=30)


def _key(token: str) -> str:
	return f"session:token:{token}"


def _user_sessions_key(user_id: UUID) -> str:
	return f"session:user:{user_id}"


async def save_token(
	token: str,
	user_id: UUID,
	payload: dict[str, Any] | None = None,
	ttl: timedelta = DEFAULT_SESSION_TTL,
) -> None:
	"""Сохранить отображение token -> user, полезную нагрузку и учесть активные токены пользователя."""

	client = get_client()
	value: dict[str, Any] = {"user_id": str(user_id)}
	if payload:
		value.update(payload)

	# сохраняем данные токена
	await client.hset(_key(token), mapping=value)
	await client.expire(_key(token), int(ttl.total_seconds()))

	# добавляем токен в множество пользователя
	await client.sadd(_user_sessions_key(user_id), token)
	await client.expire(_user_sessions_key(user_id), int(ttl.total_seconds()))


async def load_token(token: str) -> dict[str, str] | None:
	"""Получить полезную нагрузку токена; вернёт None, если токен отсутствует."""

	client = get_client()
	data = await client.hgetall(_key(token))
	return data or None


async def touch_token(
	token: str,
	user_id: UUID,
	ttl: timedelta = DEFAULT_SESSION_TTL,
) -> None:
	"""Продлить TTL токена и множества сессий (скользящая экспирация)."""

	client = get_client()
	await client.expire(_key(token), int(ttl.total_seconds()))
	await client.expire(_user_sessions_key(user_id), int(ttl.total_seconds()))


async def update_token_data(token: str, data: dict[str, str]) -> None:
	"""Обновить поля в хеше сессионного токена (например, has_pin)."""

	client = get_client()
	await client.hset(_key(token), mapping=data)


async def delete_token(token: str) -> None:
	"""Удалить токен и его связь с пользователем."""

	client = get_client()
	data = await load_token(token)
	if not data:
		return
	await client.delete(_key(token))
	await client.srem(_user_sessions_key(UUID(data["user_id"])), token)


async def revoke_all(user_id: UUID) -> None:
	"""Удалить все активные токены указанного пользователя."""

	client = get_client()
	tokens = await client.smembers(_user_sessions_key(user_id))
	if not tokens:
		return

	keys = [_key(t) for t in tokens]
	keys.append(_user_sessions_key(user_id))
	await client.delete(*keys)


__all__ = [
	"DEFAULT_SESSION_TTL",
	"delete_token",
	"load_token",
	"revoke_all",
	"save_token",
	"touch_token",
	"update_token_data",
]
