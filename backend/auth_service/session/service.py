"""Бизнес-логика управления сессиями и самоблокировки аккаунта."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shared.rabbitmq import (
	LOG_AUTH_KEY,
	send_log,
	send_notification,
)
from shared.redis_sessions import tokens as session_tokens

from ..repository import AuthRepository
from ..exceptions import (
	AuthAlreadyBlocked,
	AuthNotFound,
)


async def logout(token: str) -> None:
	"""Завершает текущую сессию пользователя.

	Args:
		token: Активный сессионный токен.
	"""
	await session_tokens.delete_token(token)


async def logout_all(user_id: UUID) -> None:
	"""Завершает все активные сессии пользователя.

	Args:
		user_id: ID пользователя.
	"""
	await session_tokens.revoke_all(user_id)


async def self_block(session: AsyncSession, user_id: UUID) -> None:
	"""Выполняет самоблокировку аккаунта по инициативе пользователя.

	Процесс включает:
	1. Установку статуса 'blocked'.
	2. Каскадную заморозку открытых счетов (frozen_by='system').
	3. Отзыв всех активных сессий (токенов).
	4. Отправку Email-уведомления и запись в лог.

	Args:
		session: Сессия БД.
		user_id: ID пользователя.

	Raises:
		AuthNotFound: Если пользователь не найден.
		AuthAlreadyBlocked: Если аккаунт уже заблокирован.
	"""
	repo = AuthRepository(session)
	user, contact = await repo.get_user_with_contact(user_id)

	if user.status == "blocked":
		raise AuthAlreadyBlocked("Аккаунт уже заблокирован.")

	now = datetime.now(UTC)
	user.status = "blocked"
	user.updated_at = now

	# Каскадная заморозка счетов
	accounts = await repo.get_open_accounts(user_id)
	for acc in accounts:
		acc.status = "frozen"
		acc.frozen_by = "system"
		acc.frozen_at = now
		acc.freeze_reason = "Самоблокировка аккаунта"

	try:
		await repo.commit()
	except Exception:
		await repo.rollback()
		raise

	# Отзыв всех сессий
	await session_tokens.revoke_all(user_id)

	# Уведомление на Email (best effort)
	try:
		await send_notification(
			notification_type="account_self_blocked",
			to=contact.email,
		)
	except Exception:
		pass

	# Логирование события
	await send_log(
		routing_key=LOG_AUTH_KEY,
		user_id=user_id,
		action="self_block",
		service="auth_service",
		details="Аккаунт заблокирован по инициативе пользователя",
	)
