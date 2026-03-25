"""Бизнес-логика входа по PIN-коду."""

import secrets
from datetime import datetime, UTC
from uuid import UUID

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.rabbitmq.client import publish
from shared.rabbitmq.constants import NOTIFICATIONS_EXCHANGE, EMAIL_ROUTING_KEY, LOGS_EXCHANGE, LOG_AUTH_KEY
from shared.redis_sessions import tokens as session_tokens
from shared.redis_sessions import rate_limit


# ── Исключения ─────────────────────────────────────────────────────────

class AuthError(Exception):
	"""Базовая ошибка аутентификации."""


class AuthNotFound(AuthError):
	"""Пользователь не найден."""


class AuthForbidden(AuthError):
	"""Неверные учётные данные."""


class AuthCooldown(AuthError):
	"""Временная блокировка из-за частых неудачных попыток."""

	def __init__(self, retry_after: int, total_failures: int):
		self.retry_after = retry_after
		self.total_failures = total_failures
		super().__init__(
			f"Слишком много неудачных попыток. Повторите через {retry_after} сек."
		)


class AuthAccountLocked(AuthError):
	"""Аккаунт заблокирован после 15 неудачных попыток."""

	def __init__(self):
		super().__init__(
			"Аккаунт заблокирован из-за многократного неверного ввода PIN-кода. "
			"Используйте /auth/request-unlock для разблокировки."
		)


# ── Вспомогательные функции ────────────────────────────────────────────

async def _find_user_by_phone(
	session: AsyncSession,
	phone: str,
) -> tuple[models.User, models.Contact]:
	"""Ищет пользователя по номеру телефона (active или blocked)."""

	from shared.utils.security import get_blind_index
	stmt = (
		select(models.User, models.Contact)
		.join(models.Contact, models.User.id == models.Contact.client_id)
		.where(
			models.Contact.phone_hash == get_blind_index(phone),
			models.User.status.in_(("active", "blocked")),
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


async def _lock_account(
	session: AsyncSession,
	user: models.User,
	email: str,
) -> None:
	"""Блокирует аккаунт пользователя (status → blocked), замораживает счета, уведомляет."""
	user.status = "blocked"

	# Каскадная заморозка all open-счетов
	stmt = (
		select(models.BankAccount)
		.where(
			models.BankAccount.client_id == user.id,
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
		acc.freeze_reason = "Блокировка аккаунта (15 неудачных PIN)"

	try:
		await session.commit()
	except Exception:
		await session.rollback()
		raise

	# Уведомляем по email
	await publish(
		exchange_name=NOTIFICATIONS_EXCHANGE,
		routing_key=EMAIL_ROUTING_KEY,
		body={
			"type": "account_locked",
			"payload": {
				"to": email,
				"variables": {},
			},
		},
	)

	# Логируем блокировку аккаунта
	try:
		await publish(
			exchange_name=LOGS_EXCHANGE,
			routing_key=LOG_AUTH_KEY,
			body={
				"type": "auth",
				"payload": {
					"user_id": str(user.id),
					"action": "account_locked",
					"service": "auth_service",
					"entity_type": "user",
					"status": "success",
					"details": "Аккаунт заблокирован (15 неудачных PIN)",
				},
			},
		)
	except Exception:
		pass


# ── Операции ───────────────────────────────────────────────────────────

async def login_pin(
	session: AsyncSession,
	phone: str,
	pin: str,
) -> tuple[str, UUID]:
	"""Вход по PIN-коду. Возвращает (token, user_id)."""

	user, contact = await _find_user_by_phone(session, phone)

	# 1. Проверка: аккаунт заблокирован?
	if user.status == "blocked":
		raise AuthAccountLocked()

	# 2. Проверка: действует ли кулдаун?
	remaining = await rate_limit.check_cooldown(phone)
	if remaining is not None:
		total = await rate_limit.get_total_failures(phone)
		raise AuthCooldown(retry_after=remaining, total_failures=total)

	# 3. Проверка: PIN установлен?
	if user.pin_hash is None:
		raise AuthForbidden(
			"PIN-код не установлен. Завершите онбординг для получения токена."
		)

	# 4. Проверка PIN
	if not _verify_pin(pin, user.pin_hash):
		total, cooldown_started, should_lock = await rate_limit.record_failure(phone)

		if should_lock:
			await _lock_account(session, user, contact.email)
			raise AuthAccountLocked()

		if cooldown_started:
			raise AuthCooldown(
				retry_after=int(rate_limit.COOLDOWN_TTL.total_seconds()),
				total_failures=total,
			)

		remaining_attempts = rate_limit.MAX_FAILURES_PER_BLOCK - (total % rate_limit.MAX_FAILURES_PER_BLOCK)
		raise AuthForbidden(
			f"Неверный PIN-код. Осталось попыток: {remaining_attempts}."
		)

	# 5. Успешный вход — сбрасываем счётчики
	await rate_limit.reset(phone)

	token = _generate_token()
	await session_tokens.save_token(token, user.id, payload={"has_pin": "true"})

	# Уведомляем о входе
	await publish(
		exchange_name=NOTIFICATIONS_EXCHANGE,
		routing_key=EMAIL_ROUTING_KEY,
		body={
			"type": "login_alert",
			"payload": {
				"to": contact.email,
				"variables": {
					"login_time": datetime.now(UTC).strftime("%d.%m.%Y %H:%M UTC"),
				},
			},
		},
	)

	# Логируем успешный вход
	try:
		await publish(
			exchange_name=LOGS_EXCHANGE,
			routing_key=LOG_AUTH_KEY,
			body={
				"type": "auth",
				"payload": {
					"user_id": str(user.id),
					"action": "login",
					"service": "auth_service",
					"entity_type": "session",
					"status": "success",
					"details": "Вход по PIN-коду",
				},
			},
		)
	except Exception:
		pass

	return token, user.id


__all__ = [
	"AuthAccountLocked",
	"AuthCooldown",
	"AuthError",
	"AuthForbidden",
	"AuthNotFound",
	"login_pin",
]
