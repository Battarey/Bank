"""Бизнес-логика восстановления доступа и сброса PIN-кода."""

from datetime import UTC, datetime

import bcrypt

from shared.events.base import LogEvent, NotificationEvent
from shared.redis_sessions import rate_limit, unlock_codes
from shared.utils.security import get_blind_index

from ..core.exceptions import (
	AuthInvalidCode,
	AuthNotFound,
)
from ..core.uow import AuthUnitOfWork


async def request_unlock(uow: AuthUnitOfWork, phone: str) -> None:
	"""Отправляет 6-значный код восстановления на привязанный Email пользователя.

	Позволяет восстановить доступ как к заблокированному аккаунту, так и сбросить забытый PIN.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		phone: Номер телефона пользователя.

	Raises:
		AuthNotFound: Если пользователь не найден.
	"""
	async with uow:
		row = await uow.users.get_by_phone(get_blind_index(phone))
		if not row:
			raise AuthNotFound(f"Пользователь с номером '{phone}' не найден.")

		user, contact = row

		# Генерация и сохранение кода (аккаунт может быть и active, если просто забыт PIN)
		code = unlock_codes.generate_code()
		await unlock_codes.save_unlock_code(user.id, code)

		# Регистрация событий (шлем на Email, который привязан к телефону)
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
				action="recovery_request",
				service="auth_service",
			)
		)

		await uow.commit()


async def confirm_unlock(uow: AuthUnitOfWork, phone: str, code: str, new_pin: str) -> None:
	"""Проверяет код и обновляет PIN-код пользователя, активируя аккаунт.

	При успешной проверке:
	1. Устанавливается новый PIN-код.
	2. Статус пользователя → 'active'.
	3. Все счета, замороженные системой, возвращаются в 'open'.
	4. Сбрасывается rate-limit попыток входа.

	Args:
		uow: Unit of Work.
		phone: Номер телефона пользователя.
		code: Код из письма.
		new_pin: Новый 4-6 значный PIN-код.

	Raises:
		AuthNotFound: Если пользователь не найден.
		AuthInvalidCode: Если код неверный или истёк.
	"""
	async with uow:
		row = await uow.users.get_by_phone(get_blind_index(phone))
		if not row:
			raise AuthNotFound(f"Пользователь с номером '{phone}' не найден.")

		user, contact = row

		# Проверка кода в Redis
		if not await unlock_codes.verify_unlock_code(user.id, code):
			raise AuthInvalidCode("Неверный или истёкший код восстановления.")

		# 1. Установка нового PIN
		salt = bcrypt.gensalt()
		user.pin_hash = bcrypt.hashpw(new_pin.encode(), salt).decode()
		user.updated_at = datetime.now(UTC)

		# 2. Активация пользователя (если был заблокирован)
		user.status = "active"

		# 3. Каскадная разморозка счетов
		frozen_accounts = await uow.users.get_system_frozen_accounts(user.id)
		for acc in frozen_accounts:
			acc.status = "open"
			acc.frozen_by = None
			acc.frozen_at = None
			acc.freeze_reason = None

		# Регистрация событий
		uow.add_event(NotificationEvent(type="pin_changed", to=contact.email))

		uow.add_event(
			LogEvent(
				user_id=user.id,
				action="recovery_success",
				service="auth_service",
				details="Доступ восстановлен и PIN изменен через Email-код",
			)
		)

		await uow.commit()

		# Сброс лимитов входа
		await rate_limit.reset(contact.phone)
