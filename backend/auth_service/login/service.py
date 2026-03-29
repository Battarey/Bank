"""Бизнес-логика входа по PIN-коду и первичной аутентификации."""

import bcrypt
from datetime import datetime, UTC
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shared.rabbitmq.client import publish
from shared.rabbitmq.constants import (
	EMAIL_ROUTING_KEY,
	LOG_AUTH_KEY,
	NOTIFICATIONS_EXCHANGE,
)
from shared.redis_sessions import rate_limit, tokens as session_tokens
from shared.utils.log_event import log_event
from shared.utils.security import get_blind_index

from ..repository import AuthRepository
from ..exceptions import (
	AuthCooldown,
	AuthForbidden,
	AuthNotFound,
)


async def login_pin(
	session: AsyncSession,
	phone: str,
	pin: str,
) -> tuple[str, UUID]:
	"""Проверяет PIN-код пользователя и создаёт сессионный токен.

	Включает проверку rate-limit для предотвращения брутфорса. 
	При успехе создаёт сессию в Redis и возвращает токен.

	Args:
		session: Сессия БД.
		phone: Номер телефона пользователя.
		pin: 4-цифровой PIN-код.

	Returns:
		tuple[str, UUID]: Сессионный токен и ID пользователя.

	Raises:
		AuthCooldown: Если превышен лимит попыток входа.
		AuthNotFound: Если пользователь с таким телефоном не зарегистрирован.
		AuthForbidden: Если PIN-код неверный или аккаунт заблокирован.
	"""
	repo = AuthRepository(session)
	
	# 1. Rate-limit check
	is_limited, retry_after, failures = await rate_limit.check(phone)
	if is_limited:
		raise AuthCooldown(
			f"Слишком много попыток входа. Повторите через {retry_after} сек.",
			retry_after=retry_after
		)

	# 2. Поиск пользователя
	row = await repo.get_by_phone(get_blind_index(phone))
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
			await _log_login_failure(user.id, f"Неудачный ввод PIN ({failures + 1}-я попытка)")
			
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

	await log_event(
		routing_key=LOG_AUTH_KEY,
		event_type="auth",
		payload={
			"user_id": str(user.id),
			"action": "login",
			"service": "auth_service",
			"status": "success",
			"details": "Успешный вход по PIN",
		}
	)

	return token, user.id


async def _log_login_failure(user_id: UUID, details: str) -> None:
	"""Вспомогательный метод для логирования подозрительных попыток входа."""
	await log_event(
		routing_key=LOG_AUTH_KEY,
		event_type="auth",
		payload={
			"user_id": str(user_id),
			"action": "login_failure",
			"service": "auth_service",
			"status": "warning",
			"details": details,
		}
	)


async def set_pin(session: AsyncSession, user_id: UUID, pin: str) -> None:
	"""Устанавливает или меняет PIN-код пользователя.

	Args:
		session: Сессия БД.
		user_id: ID пользователя.
		pin: Новый 4-цифровой PIN-код.

	Raises:
		AuthNotFound: Если пользователь не найден.
	"""
	repo = AuthRepository(session)
	user = await repo.get(user_id)
	if not user:
		raise AuthNotFound("Пользователь не найден.")

	# Хеширование PIN
	salt = bcrypt.gensalt()
	user.pin_hash = bcrypt.hashpw(pin.encode(), salt).decode()
	user.updated_at = datetime.now(UTC)

	await repo.commit()

	await log_event(
		routing_key=LOG_AUTH_KEY,
		event_type="auth",
		payload={
			"user_id": str(user_id),
			"action": "set_pin",
			"service": "auth_service",
			"status": "success",
		}
	)
