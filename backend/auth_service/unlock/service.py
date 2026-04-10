"""Бизнес-логика разблокировки аккаунта по Email-коду."""

from shared.events.base import LogEvent, NotificationEvent
from shared.redis_sessions import rate_limit, unlock_codes
from shared.utils.security import get_blind_index

from ..exceptions import (
	AuthInvalidCode,
	AuthNotBlocked,
	AuthNotFound,
)
from ..uow import AuthUnitOfWork


async def request_unlock(uow: AuthUnitOfWork, email: str) -> None:
	"""Отправляет 6-значный код разблокировки на Email пользователя.

	Проверяет, что аккаунт действительно заблокирован, генерирует код и сохраняет его в Redis.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		email: Email пользователя.

	Raises:
		AuthNotFound: Если пользователь не найден.
		AuthNotBlocked: Если аккаунт не в статусе 'blocked'.
	"""
	async with uow:
		row = await uow.users.get_by_email(get_blind_index(email))
		if not row:
			raise AuthNotFound(f"Пользователь с email '{email}' не найден.")

		user, contact = row

		if user.status != "blocked":
			raise AuthNotBlocked("Аккаунт не заблокирован. Восстановление доступа не требуется.")

		# Генерация и сохранение кода
		code = unlock_codes.generate_code()
		await unlock_codes.save_unlock_code(user.id, code)

		# Регистрация событий
		uow.add_event(
			NotificationEvent(
				type="unlock_code",
				to=contact.email,
				variables={"code": code},
			)
		)

		uow.add_event(
			LogEvent(
				user_id=user.id,
				action="unlock_request",
				service="auth_service",
			)
		)

		await uow.commit()


async def confirm_unlock(uow: AuthUnitOfWork, email: str, code: str) -> None:
	"""Проверяет код и разблокирует аккаунт.

	При успешной проверке:
	1. Статус пользователя → 'active'.
	2. Все счета, замороженные системой, возвращаются в 'open'.
	3. Сбрасывается rate-limit попыток входа (по телефону).
	4. Регистрация событий NotificationEvent и LogEvent.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		email: Email пользователя.
		code: Код из письма.

	Raises:
		AuthNotFound: Если пользователь не найден.
		AuthNotBlocked: Если аккаунт не заблокирован.
		AuthInvalidCode: Если код неверный или истёк.
	"""
	async with uow:
		row = await uow.users.get_by_email(get_blind_index(email))
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
		frozen_accounts = await uow.users.get_system_frozen_accounts(user.id)
		for acc in frozen_accounts:
			acc.status = "open"
			acc.frozen_by = None
			acc.frozen_at = None
			acc.freeze_reason = None

		# Регистрация событий
		uow.add_event(
			NotificationEvent(
				type="account_unlocked",
				to=contact.email,
			)
		)

		uow.add_event(
			LogEvent(
				user_id=user.id,
				action="unlock",
				service="auth_service",
				details="Доступ восстановлен по Email-коду",
			)
		)

		await uow.commit()

		# Сброс лимитов входа (после успешного коммита)
		await rate_limit.reset(contact.phone)
