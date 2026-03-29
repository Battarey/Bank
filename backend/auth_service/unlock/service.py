"""Бизнес-логика разблокировки аккаунта по Email-коду."""

from sqlalchemy.ext.asyncio import AsyncSession

from shared.rabbitmq.client import publish
from shared.rabbitmq.constants import (
	EMAIL_ROUTING_KEY,
	LOG_AUTH_KEY,
	NOTIFICATIONS_EXCHANGE,
)
from shared.redis_sessions import rate_limit, unlock_codes
from shared.utils.log_event import log_event
from shared.utils.security import get_blind_index

from ..repository import AuthRepository
from ..exceptions import (
	AuthInvalidCode,
	AuthNotBlocked,
	AuthNotFound,
)


async def request_unlock(session: AsyncSession, email: str) -> None:
	"""Отправляет 6-значный код разблокировки на Email пользователя.

	Проверяет, что аккаунт действительно заблокирован, генерирует код и сохраняет его в Redis.

	Args:
		session: Сессия БД.
		email: Email пользователя.

	Raises:
		AuthNotFound: Если пользователь не найден.
		AuthNotBlocked: Если аккаунт не в статусе 'blocked'.
	"""
	repo = AuthRepository(session)
	row = await repo.get_by_email(get_blind_index(email))
	if not row:
		raise AuthNotFound(f"Пользователь с email '{email}' не найден.")
	
	user, contact = row

	if user.status != "blocked":
		raise AuthNotBlocked("Аккаунт не заблокирован. Восстановление доступа не требуется.")

	# Генерация и сохранение кода
	code = unlock_codes.generate_code()
	await unlock_codes.save_unlock_code(user.id, code)

	# Отправка Email-уведомления
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

	await log_event(
		routing_key=LOG_AUTH_KEY,
		event_type="auth",
		payload={
			"user_id": str(user.id),
			"action": "unlock_request",
			"service": "auth_service",
			"status": "success",
		}
	)


async def confirm_unlock(session: AsyncSession, email: str, code: str) -> None:
	"""Проверяет код и разблокирует аккаунт.

	При успешной проверке:
	1. Статус пользователя → 'active'.
	2. Все счета, замороженные системой, возвращаются в 'open'.
	3. Сбрасывается rate-limit попыток входа (по телефону).

	Args:
		session: Сессия БД.
		email: Email пользователя.
		code: Код из письма.

	Raises:
		AuthInvalidCode: Если код неверный или истёк.
	"""
	repo = AuthRepository(session)
	row = await repo.get_by_email(get_blind_index(email))
	if not row:
		raise AuthNotFound(f"Пользователь с email '{email}' не найден.")
	
	user, contact = row

	if user.status != "blocked":
		raise AuthNotBlocked("Аккаунт не заблокирован.")

	# Проверка кода в Redis
	if not await unlock_codes.verify_unlock_code(user.id, code):
		raise AuthInvalidCode("Неверный или истёкший код разблокировки.")

	# Активация пользователя
	user.status = "active"

	# Каскадная разморозка счетов
	frozen_accounts = await repo.get_system_frozen_accounts(user.id)
	for acc in frozen_accounts:
		acc.status = "open"
		acc.frozen_by = None
		acc.frozen_at = None
		acc.freeze_reason = None

	try:
		await repo.commit()
	except Exception:
		await repo.rollback()
		raise

	# Сброс лимитов входа
	await rate_limit.reset(contact.phone)

	# Уведомления и лог
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

	await log_event(
		routing_key=LOG_AUTH_KEY,
		event_type="auth",
		payload={
			"user_id": str(user.id),
			"action": "unlock",
			"service": "auth_service",
			"status": "success",
			"details": "Доступ восстановлен по Email-коду",
		}
	)
