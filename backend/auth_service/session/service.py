"""Бизнес-логика управления сессиями и PIN-кодом."""

from datetime import UTC, datetime
from uuid import UUID

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.rabbitmq.client import publish
from shared.rabbitmq.constants import NOTIFICATIONS_EXCHANGE, EMAIL_ROUTING_KEY, LOGS_EXCHANGE, LOG_AUTH_KEY
from shared.redis_sessions import tokens as session_tokens


# ── Исключения ─────────────────────────────────────────────────────────

class SessionError(Exception):
	"""Базовая ошибка сессионных операций."""


class SessionNotFound(SessionError):
	"""Пользователь не найден."""


class SessionAlreadyBlocked(SessionError):
	"""Аккаунт уже заблокирован."""


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

	# Уведомляем об изменении PIN
	contact = await session.get(models.Contact, user_id)
	if contact:
		await publish(
			exchange_name=NOTIFICATIONS_EXCHANGE,
			routing_key=EMAIL_ROUTING_KEY,
			body={
				"type": "pin_changed",
				"payload": {
					"to": contact.email,
					"variables": {},
				},
			},
		)

	# Логируем изменение PIN
	try:
		await publish(
			exchange_name=LOGS_EXCHANGE,
			routing_key=LOG_AUTH_KEY,
			body={
				"type": "auth",
				"payload": {
					"user_id": str(user_id),
					"action": "set_pin",
					"service": "auth_service",
					"entity_type": "user",
					"status": "success",
					"details": "PIN-код установлен / изменён",
				},
			},
		)
	except Exception:
		pass


async def logout(token: str) -> None:
	"""Завершает текущий сеанс (удаляет токен)."""

	await session_tokens.delete_token(token)


async def logout_all(user_id: UUID) -> None:
	"""Завершает все сеансы пользователя."""

	await session_tokens.revoke_all(user_id)


async def self_block(session: AsyncSession, user_id: UUID, token: str) -> None:
	"""Самоблокировка аккаунта по запросу пользователя.

	1. Устанавливает user.status → blocked.
	2. Каскадно замораживает все open-счета (frozen_by=system).
	3. Завершает все сессии.
	4. Отправляет email-уведомление.
	"""

	user = await session.get(models.User, user_id)
	if user is None:
		raise SessionNotFound("Пользователь не найден.")

	if user.status == "blocked":
		raise SessionAlreadyBlocked("Аккаунт уже заблокирован.")

	user.status = "blocked"

	# Каскадная заморозка open-счетов
	stmt = (
		select(models.BankAccount)
		.where(
			models.BankAccount.client_id == user_id,
			models.BankAccount.status == "open",
		)
		.with_for_update()
	)
	result = await session.execute(stmt)
	accounts = result.scalars().all()
	now = datetime.now(UTC)
	for acc in accounts:
		acc.status = "frozen"
		acc.frozen_by = "system"
		acc.frozen_at = now
		acc.freeze_reason = "Самоблокировка аккаунта"

	try:
		await session.commit()
	except Exception:
		await session.rollback()
		raise

	# Завершаем все сессии
	await session_tokens.revoke_all(user_id)

	# Уведомляем
	contact = await session.get(models.Contact, user_id)
	if contact:
		try:
			await publish(
				exchange_name=NOTIFICATIONS_EXCHANGE,
				routing_key=EMAIL_ROUTING_KEY,
				body={
					"type": "account_self_blocked",
					"payload": {
						"to": contact.email,
						"variables": {},
					},
				},
			)
		except Exception:
			pass  # уведомление не критично

	# Логируем самоблокировку
	try:
		await publish(
			exchange_name=LOGS_EXCHANGE,
			routing_key=LOG_AUTH_KEY,
			body={
				"type": "auth",
				"payload": {
					"user_id": str(user_id),
					"action": "self_block",
					"service": "auth_service",
					"entity_type": "user",
					"status": "success",
					"details": "Самоблокировка аккаунта",
				},
			},
		)
	except Exception:
		pass


__all__ = [
	"SessionAlreadyBlocked",
	"SessionError",
	"SessionNotFound",
	"logout",
	"logout_all",
	"self_block",
	"set_pin",
]
