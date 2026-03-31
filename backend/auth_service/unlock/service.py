"""Бизнес-логика разблокировки аккаунта по Email-коду."""

from sqlalchemy.ext.asyncio import AsyncSession

from shared.rabbitmq import (
	LOG_AUTH_KEY,
	send_log,
	send_notification,
)
from shared.redis_sessions import rate_limit, unlock_codes
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
	await send_notification(
		notification_type="unlock_code",
		to=contact.email,
		variables={"code": code},
	)

	await send_log(
		routing_key=LOG_AUTH_KEY,
		user_id=user.id,
		action="unlock_request",
		service="auth_service",
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
	await send_notification(
		notification_type="account_unlocked",
		to=contact.email,
	)

	await send_log(
		routing_key=LOG_AUTH_KEY,
		user_id=user.id,
		action="unlock",
		service="auth_service",
		details="Доступ восстановлен по Email-коду",
	)
