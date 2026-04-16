"""Бизнес-логика входа по PIN-коду и первичной аутентификации."""

from datetime import UTC, datetime
from uuid import UUID

import bcrypt

from shared.events.base import LogEvent, NotificationEvent
from shared.redis_sessions import rate_limit
from shared.redis_sessions import tokens as session_tokens
from shared.utils.security import get_blind_index

from ..core.exceptions import (
	AuthCooldown,
	AuthForbidden,
	AuthNotFound,
)
from ..core.uow import AuthUnitOfWork


async def login_pin(
	uow: AuthUnitOfWork,
	phone: str,
	pin: str,
) -> tuple[str, str, UUID]:
	"""Проверяет PIN-код пользователя и создаёт пару сессионных токенов.

	Включает проверку rate-limit для предотвращения брутфорса.
	При успехе создаёт сессию и токен привязки (refresh) в Redis.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		phone: Номер телефона пользователя.
		pin: 4-цифровой PIN-код.

	Returns:
		tuple[str, str, UUID]: session_token, refresh_token и ID пользователя.

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
				f"Слишком много попыток входа. Повторите через {retry_after} сек.", retry_after=retry_after
			)

		# 2. Поиск пользователя
		row = await uow.users.get_by_phone(get_blind_index(phone))
		if not row:
			raise AuthNotFound("Пользователь с таким номером телефона не найден.")

		user, _contact = row

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
				uow.add_event(
					LogEvent(
						user_id=user.id,
						action="login_failure",
						service="auth_service",
						status="warning",
						details=f"Неудачный ввод PIN ({failures + 1}-я попытка)",
					)
				)

			raise AuthForbidden("Неверный PIN-код.")

		# 5. Успех: сброс лимитов и создание сессий
		await rate_limit.reset(phone)

		session_token = await session_tokens.create_token(
			user_id=user.id,
			data={
				"phone": phone,
				"status": user.status,
				"has_pin": "true",
			},
		)
		refresh_token = await session_tokens.create_refresh_token(user_id=user.id)

		uow.add_event(
			LogEvent(
				user_id=user.id,
				action="login",
				service="auth_service",
				status="success",
				details="Успешный вход по PIN",
			)
		)

		await uow.commit()
		return session_token, refresh_token, user.id


async def login_quick(
	uow: AuthUnitOfWork,
	refresh_token: str,
	pin: str,
) -> tuple[str, str, UUID]:
	"""Быстрый вход по токену привязки и PIN-коду.

	Выполняет ротацию Refresh Token: старый удаляется, выдается новый.

	Args:
		uow: Unit of Work.
		refresh_token: Ранее выданный токен привязки.
		pin: 4-цифровой PIN-код.

	Returns:
		tuple[str, str, UUID]: Новая пара токенов и ID пользователя.

	Raises:
		AuthForbidden: Если токен невалиден или PIN неверный.
		AuthNotFound: Если пользователь не найден.
	"""
	# 1. Проверка существования рефреш-токена
	user_id = await session_tokens.load_refresh_token(refresh_token)
	if not user_id:
		raise AuthForbidden("Токен привязки недействителен или истек.")

	async with uow:
		# 2. Получение пользователя (с контактами для логов)
		user, contact = await uow.users.get_user_with_contact(user_id)

		# 3. Проверка статуса
		if user.status != "active":
			raise AuthForbidden(f"Аккаунт находится в статусе '{user.status}'.")

		# 4. Проверка PIN
		if not user.pin_hash or not bcrypt.checkpw(pin.encode(), user.pin_hash.encode()):
			# Для быстрого входа тоже можно считать попытки (по телефону из контакта)
			await rate_limit.increment(contact.phone)
			raise AuthForbidden("Неверный PIN-код.")

		# 5. Успех: ротация токенов
		await session_tokens.delete_refresh_token(refresh_token)

		new_session = await session_tokens.create_token(
			user_id=user.id,
			data={
				"phone": contact.phone,
				"status": user.status,
				"has_pin": "true",
			},
		)
		new_refresh = await session_tokens.create_refresh_token(user_id=user.id)

		uow.add_event(
			LogEvent(
				user_id=user.id,
				action="quick_login",
				service="auth_service",
				status="success",
				details="Вход по токену привязки и PIN",
			)
		)

		await uow.commit()
		return new_session, new_refresh, user.id


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
		uow.add_event(
			LogEvent(
				user_id=user_id,
				action="set_pin",
				service="auth_service",
				status="success",
			)
		)

		# Событие уведомления
		uow.add_event(NotificationEvent(type="pin_changed", to=contact.email))

		await uow.commit()
