"""Хранение и проверка кодов подтверждения email в Redis (onboarding)."""

import hmac
import secrets
from datetime import timedelta
from uuid import UUID

from .client import get_client

DEFAULT_CODE_TTL = timedelta(minutes=10)
SEND_COOLDOWN = timedelta(minutes=2)
CODE_LENGTH = 6


def generate_code() -> str:
	"""Генерирует случайный цифровой код длиной CODE_LENGTH."""
	return "".join(str(secrets.randbelow(10)) for _ in range(CODE_LENGTH))


def _code_key(user_id: UUID) -> str:
	return f"onboarding:{user_id}:email_code"


def _verified_key(user_id: UUID) -> str:
	return f"onboarding:{user_id}:email_verified"


def _cooldown_key(user_id: UUID) -> str:
	return f"onboarding:{user_id}:email_send_cooldown"


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


async def has_email_code(user_id: UUID) -> bool:
	"""Проверить, существует ли уже активный код подтверждения в Redis."""

	client = get_client()
	return await client.exists(_code_key(user_id)) > 0


async def get_remaining_cooldown(user_id: UUID) -> int:
	"""Возвращает оставшееся время кулдауна в секундах. 0 если отправка разрешена."""

	client = get_client()
	ttl = await client.ttl(_cooldown_key(user_id))
	return max(0, ttl) if ttl > 0 else 0


async def set_send_cooldown(user_id: UUID, ttl: timedelta = SEND_COOLDOWN) -> None:
	"""Установить блокировку на повторную отправку письма."""

	client = get_client()
	await client.set(_cooldown_key(user_id), "1", ex=int(ttl.total_seconds()))


async def clear_email_verification(user_id: UUID) -> None:
	"""Удалить все данные верификации email (код + флаг)."""

	client = get_client()
	await client.delete(_code_key(user_id), _verified_key(user_id))


__all__ = [
	"CODE_LENGTH",
	"clear_email_verification",
	"generate_code",
	"get_remaining_cooldown",
	"has_email_code",
	"is_email_verified",
	"save_email_code",
	"set_send_cooldown",
	"verify_email_code",
]
