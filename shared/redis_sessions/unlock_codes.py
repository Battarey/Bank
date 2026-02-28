"""Хранение и проверка кодов разблокировки аккаунта в Redis (sessions)."""

import hmac
import secrets
from datetime import timedelta
from uuid import UUID

from .client import get_client

DEFAULT_CODE_TTL = timedelta(minutes=10)
CODE_LENGTH = 6


def generate_code() -> str:
	"""Генерирует случайный цифровой код длиной CODE_LENGTH."""
	return "".join(str(secrets.randbelow(10)) for _ in range(CODE_LENGTH))


def _code_key(user_id: UUID) -> str:
	return f"unlock:{user_id}:code"


async def save_unlock_code(
	user_id: UUID,
	code: str,
	ttl: timedelta = DEFAULT_CODE_TTL,
) -> None:
	"""Сохранить код разблокировки с TTL."""
	client = get_client()
	await client.set(_code_key(user_id), code, ex=int(ttl.total_seconds()))


async def verify_unlock_code(user_id: UUID, code: str) -> bool:
	"""Проверить код разблокировки.

	Если код верный — удаляет его и возвращает True.
	Если неверный/истёк — возвращает False.
	"""
	client = get_client()
	stored = await client.get(_code_key(user_id))
	if stored is None or not hmac.compare_digest(stored, code):
		return False

	await client.delete(_code_key(user_id))
	return True


async def clear_unlock_code(user_id: UUID) -> None:
	"""Удалить код разблокировки (если есть)."""
	client = get_client()
	await client.delete(_code_key(user_id))


__all__ = [
	"CODE_LENGTH",
	"DEFAULT_CODE_TTL",
	"clear_unlock_code",
	"generate_code",
	"save_unlock_code",
	"verify_unlock_code",
]
