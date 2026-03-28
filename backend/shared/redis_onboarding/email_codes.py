"""Хранение и проверка кодов подтверждения email в Redis (onboarding)."""

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
	return f"onboarding:{user_id}:email_code"


def _verified_key(user_id: UUID) -> str:
	return f"onboarding:{user_id}:email_verified"


async def save_email_code(
	user_id: UUID,
	code: str,
	ttl: timedelta = DEFAULT_CODE_TTL,
) -> None:
	"""Сохранить код подтверждения email с TTL."""

	client = get_client()
	await client.set(_code_key(user_id), code, ex=int(ttl.total_seconds()))


async def verify_email_code(user_id: UUID, code: str) -> bool:
	"""Проверить код. Если совпадает — удаляет код и ставит флаг email_verified.

	Возвращает True при успешной верификации, False если код неверный/истёк.
	"""

	client = get_client()
	stored = await client.get(_code_key(user_id))
	if stored is None or not hmac.compare_digest(stored, code):
		return False

	# Код верный — помечаем email как подтверждённый
	await client.delete(_code_key(user_id))
	await client.set(_verified_key(user_id), "1", ex=int(timedelta(hours=24).total_seconds()))
	return True


async def is_email_verified(user_id: UUID) -> bool:
	"""Проверить, подтверждён ли email для данного пользователя."""

	client = get_client()
	return await client.get(_verified_key(user_id)) == "1"


async def clear_email_verification(user_id: UUID) -> None:
	"""Удалить все данные верификации email (код + флаг)."""

	client = get_client()
	await client.delete(_code_key(user_id), _verified_key(user_id))


__all__ = [
	"CODE_LENGTH",
	"clear_email_verification",
	"generate_code",
	"is_email_verified",
	"save_email_code",
	"verify_email_code",
]
