"""Бизнес-логика разблокировки аккаунта.

Поток:
1. POST /request-unlock {phone} — отправляет 6-значный код на email.
2. POST /unlock {phone, code} — проверяет код, снимает блокировку.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.rabbitmq.client import publish
from shared.rabbitmq.constants import NOTIFICATIONS_EXCHANGE, EMAIL_ROUTING_KEY, LOGS_EXCHANGE, LOG_AUTH_KEY
from shared.redis_sessions import rate_limit
from shared.redis_sessions import unlock_codes


# ── Исключения ─────────────────────────────────────────────────────────

class UnlockError(Exception):
	"""Базовая ошибка разблокировки."""


class UnlockNotFound(UnlockError):
	"""Пользователь не найден."""


class UnlockNotBlocked(UnlockError):
	"""Аккаунт не заблокирован."""


class UnlockInvalidCode(UnlockError):
	"""Неверный или истёкший код разблокировки."""


# ── Вспомогательные ────────────────────────────────────────────────────

async def _find_user_by_email(
	session: AsyncSession,
	email: str,
) -> tuple[models.User, models.Contact]:
	"""Ищет пользователя по email."""

	stmt = (
		select(models.User, models.Contact)
		.join(models.Contact, models.User.id == models.Contact.client_id)
		.where(models.Contact.email == email)
	)
	result = await session.execute(stmt)
	row = result.first()
	if row is None:
		raise UnlockNotFound("Пользователь с таким email не найден.")
	return row.tuple()


# ── Операции ───────────────────────────────────────────────────────────

async def request_unlock(session: AsyncSession, email: str) -> None:
	"""Отправить код разблокировки на email пользователя."""

	user, contact = await _find_user_by_email(session, email)

	if user.status != "blocked":
		raise UnlockNotBlocked("Аккаунт не заблокирован.")

	code = unlock_codes.generate_code()
	await unlock_codes.save_unlock_code(user.id, code)

	# Отправляем email через RabbitMQ
	await publish(
		exchange_name=NOTIFICATIONS_EXCHANGE,
		routing_key=EMAIL_ROUTING_KEY,
		body={
			"type": "unlock_code",
			"payload": {
				"to": contact.email,
				"variables": {"code": code},
			},
		},
	)


async def unlock_account(session: AsyncSession, email: str, code: str) -> None:
	"""Проверить код и разблокировать аккаунт."""

	user, contact = await _find_user_by_email(session, email)

	if user.status != "blocked":
		raise UnlockNotBlocked("Аккаунт не заблокирован.")

	# Проверяем код
	valid = await unlock_codes.verify_unlock_code(user.id, code)
	if not valid:
		raise UnlockInvalidCode("Неверный или истёкший код разблокировки.")

	# Разблокируем
	user.status = "active"

	# Каскадная разморозка системно-замороженных счетов
	stmt_freeze = (
		select(models.BankAccount)
		.where(
			models.BankAccount.client_id == user.id,
			models.BankAccount.status == "frozen",
			models.BankAccount.frozen_by == "system",
		)
		.with_for_update()
	)
	result_freeze = await session.execute(stmt_freeze)
	frozen_accounts = result_freeze.scalars().all()
	for acc in frozen_accounts:
		acc.status = "open"
		acc.frozen_by = None
		acc.frozen_at = None
		acc.freeze_reason = None

	try:
		await session.commit()
	except Exception:
		await session.rollback()
		raise

	# Сбрасываем rate-limit по телефону
	await rate_limit.reset(contact.phone)

	# Уведомляем пользователя
	await publish(
		exchange_name=NOTIFICATIONS_EXCHANGE,
		routing_key=EMAIL_ROUTING_KEY,
		body={
			"type": "account_unlocked",
			"payload": {
				"to": contact.email,
				"variables": {},
			},
		},
	)

	# Логируем разблокировку
	try:
		await publish(
			exchange_name=LOGS_EXCHANGE,
			routing_key=LOG_AUTH_KEY,
			body={
				"type": "auth",
				"payload": {
					"user_id": str(user.id),
					"action": "unlock",
					"service": "auth_service",
					"entity_type": "user",
					"status": "success",
					"details": "Аккаунт разблокирован по коду",
				},
			},
		)
	except Exception:
		pass


__all__ = [
	"UnlockError",
	"UnlockInvalidCode",
	"UnlockNotBlocked",
	"UnlockNotFound",
	"request_unlock",
	"unlock_account",
]
