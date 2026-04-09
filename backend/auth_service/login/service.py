"""Бизнес-логика входа по PIN-коду и первичной аутентификации."""

import bcrypt
from datetime import datetime, UTC
from uuid import UUID

from shared.events.base import LogEvent, NotificationEvent
from shared.utils.security import get_blind_index
from shared.redis_sessions import rate_limit, tokens as session_tokens
from ..uow import AuthUnitOfWork
from ..exceptions import (
	AuthCooldown,
	AuthForbidden,
	AuthNotFound,
)


async def login_pin(
	uow: AuthUnitOfWork,
	phone: str,
	pin: str,
) -> tuple[str, UUID]:
	"""Проверяет PIN-код пользователя и создаёт сессионный токен.

	Включает проверку rate-limit для предотвращения брутфорса. 
	При успехе создаёт сессию в Redis и возвращает токен.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		phone: Номер телефона пользователя.
		pin: 4-цифровой PIN-код.

	Returns:
		tuple[str, UUID]: Сессионный токен и ID пользователя.

	Raises:
		AuthCooldown: Если превышен лимит попыток входа.
		AuthNotFound: Если пользователь с таким номером телефона не найден.
		AuthForbidden: Если PIN-код неверный или аккаунт заблокирован.
	"""
	async with uow:
		# 1. Rate-limit check
		is_limited, retry_after, failures = await rate_limit.check(phone)
		if is_limited:
			raise AuthCooldown(
				f"Слишком много попыток входа. Повторите через {retry_after} сек.",
				retry_after=retry_after
			)

		# 2. Поиск пользователя
		row = await uow.users.get_by_phone(get_blind_index(phone))
		if not row:
			raise AuthNotFound("Пользователь с таким номером телефона не найден.")
		
		user, contact = row

		# 3. Проверка статуса
		if user.status == "blocked":
			raise AuthForbidden("Аккаунт заблокирован. Воспользуйтесь восстановлением доступа.")
		if user.status == "deleted":
			raise AuthForbidden("Аккаунт удалён.")

		# 4. Проверка PIN
		if not user.pin_hash or not bcrypt.checkpw(pin.encode(), user.pin_hash.encode()):
			await rate_limit.increment(phone)
			
			# Если это 5-я попытка (или кратная 5) — лог в аудит
			if (failures + 1) % 5 == 0:
				uow.add_event(LogEvent(
					user_id=user.id,
					action="login_failure",
					service="auth_service",
					status="warning",
					details=f"Неудачный ввод PIN ({failures + 1}-я попытка)",
				))
				
			raise AuthForbidden("Неверный PIN-код.")

		# 5. Успех: сброс лимитов и создание сессии
		await rate_limit.reset(phone)
		
		token = await session_tokens.create_token(
			user_id=user.id,
			data={
				"phone": phone,
				"status": user.status,
				"has_pin": "true",
			}
		)

		uow.add_event(LogEvent(
			user_id=user.id,
			action="login",
			service="auth_service",
			status="success",
			details="Успешный вход по PIN",
		))

		await uow.commit()
		return token, user.id


async def set_pin(uow: AuthUnitOfWork, user_id: UUID, pin: str) -> None:
	"""Устанавливает или меняет PIN-код пользователя.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		user_id: ID пользователя.
		pin: Новый 4-цифровой PIN-код.

	Raises:
		AuthNotFound: Если пользователь не найден.
	"""
	async with uow:
		# Получаем пользователя вместе с контактными данными (email)
		user, contact = await uow.users.get_user_with_contact(user_id)

		# Хеширование PIN
		salt = bcrypt.gensalt()
		user.pin_hash = bcrypt.hashpw(pin.encode(), salt).decode()
		user.updated_at = datetime.now(UTC)

		# Событие лога
		uow.add_event(LogEvent(
			user_id=user_id,
			action="set_pin",
			service="auth_service",
			status="success",
		))

		# Событие уведомления
		uow.add_event(NotificationEvent(
			type="pin_changed",
			to=contact.email
		))

		await uow.commit()
