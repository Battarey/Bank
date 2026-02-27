"""Бизнес-логика входа по PIN-коду."""

import secrets
from uuid import UUID

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.redis_sessions import tokens as session_tokens


# ── Исключения ─────────────────────────────────────────────────────────

class AuthError(Exception):
	"""Базовая ошибка аутентификации."""


class AuthNotFound(AuthError):
	"""Пользователь не найден."""


class AuthForbidden(AuthError):
	"""Неверные учётные данные."""


# ── Вспомогательные функции ────────────────────────────────────────────

async def _find_user_by_phone(
	session: AsyncSession,
	phone: str,
) -> tuple[models.User, models.Contact]:
	"""Ищет активного пользователя по номеру телефона."""

	stmt = (
		select(models.User, models.Contact)
		.join(models.Contact, models.User.id == models.Contact.client_id)
		.where(
			models.Contact.phone == phone,
			models.User.status == "active",
		)
	)
	result = await session.execute(stmt)
	row = result.first()
	if row is None:
		raise AuthNotFound(
			"Пользователь с таким номером не найден или неактивен."
		)
	return row.tuple()


def _verify_pin(pin: str, pin_hash: str) -> bool:
	return bcrypt.checkpw(pin.encode(), pin_hash.encode())


def _generate_token() -> str:
	return secrets.token_urlsafe(32)


# ── Операции ───────────────────────────────────────────────────────────

async def login_pin(
	session: AsyncSession,
	phone: str,
	pin: str,
) -> tuple[str, UUID]:
	"""Вход по PIN-коду. Возвращает (token, user_id)."""

	user, _ = await _find_user_by_phone(session, phone)

	if user.pin_hash is None:
		raise AuthForbidden(
			"PIN-код не установлен. Завершите онбординг для получения токена."
		)

	if not _verify_pin(pin, user.pin_hash):
		raise AuthForbidden("Неверный PIN-код.")

	token = _generate_token()
	await session_tokens.save_token(token, user.id)
	return token, user.id


__all__ = [
	"AuthError",
	"AuthForbidden",
	"AuthNotFound",
	"login_pin",
]
