"""Бизнес-логика управления сессиями и PIN-кодом."""

from uuid import UUID

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.redis_sessions import tokens as session_tokens


# ── Исключения ─────────────────────────────────────────────────────────

class SessionError(Exception):
	"""Базовая ошибка сессионных операций."""


class SessionNotFound(SessionError):
	"""Пользователь не найден."""


# ── Вспомогательные ────────────────────────────────────────────────────

def _hash_pin(pin: str) -> str:
	return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()


# ── Операции ───────────────────────────────────────────────────────────

async def set_pin(session: AsyncSession, user_id: UUID, pin: str) -> None:
	"""Устанавливает или обновляет PIN-код."""

	user = await session.get(models.User, user_id)
	if user is None:
		raise SessionNotFound("Пользователь не найден.")

	user.pin_hash = _hash_pin(pin)

	try:
		await session.commit()
	except Exception:
		await session.rollback()
		raise


async def logout(token: str) -> None:
	"""Завершает текущий сеанс (удаляет токен)."""

	await session_tokens.delete_token(token)


async def logout_all(user_id: UUID) -> None:
	"""Завершает все сеансы пользователя."""

	await session_tokens.revoke_all(user_id)


__all__ = [
	"SessionError",
	"SessionNotFound",
	"logout",
	"logout_all",
	"set_pin",
]
