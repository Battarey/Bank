"""Бизнес-логика управления сессиями и самоблокировки аккаунта."""

from datetime import UTC, datetime
from uuid import UUID

from shared.events.base import LogEvent, NotificationEvent
from ..uow import AuthUnitOfWork
from ..exceptions import (
	AuthAlreadyBlocked,
	AuthNotFound,
)


async def logout(token: str) -> None:
	"""Завершает текущую сессию пользователя.

	Удаляет сессионный токен из Redis.

	Args:
		token: Активный сессионный токен.
	"""
	await session_tokens.delete_token(token)


async def logout_all(user_id: UUID) -> None:
	"""Завершает все активные сессии пользователя.

	Отзывает все токены пользователя в Redis.

	Args:
		user_id: ID пользователя.
	"""
	await session_tokens.revoke_all(user_id)


async def self_block(uow: AuthUnitOfWork, user_id: UUID) -> None:
	"""Выполняет самоблокировку аккаунта по инициативе пользователя.

	Процесс включает:
	1. Установку статуса 'blocked'.
	2. Каскадную заморозку открытых счетов (frozen_by='system').
	3. Отзыв всех активных сессий (токенов).
	4. Регистрация событий NotificationEvent и LogEvent.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		user_id: ID пользователя.

	Raises:
		AuthNotFound: Если пользователь не найден.
		AuthAlreadyBlocked: Если аккаунт уже заблокирован.
	"""
	async with uow:
		user, contact = await uow.users.get_user_with_contact(user_id)

		if user.status == "blocked":
			raise AuthAlreadyBlocked("Аккаунт уже заблокирован.")

		now = datetime.now(UTC)
		user.status = "blocked"
		user.updated_at = now

		# Каскадная заморозка счетов
		accounts = await uow.users.get_open_accounts(user_id)
		for acc in accounts:
			acc.status = "frozen"
			acc.frozen_by = "system"
			acc.frozen_at = now
			acc.freeze_reason = "Самоблокировка аккаунта"

		# Регистрация событий
		uow.add_event(NotificationEvent(
			type="account_self_blocked",
			to=contact.email,
		))

		uow.add_event(LogEvent(
			user_id=user_id,
			action="self_block",
			service="auth_service",
			details="Аккаунт заблокирован по инициативе пользователя",
		))

		await uow.commit()

		# Отзыв всех сессий (после успешного коммита)
		await session_tokens.revoke_all(user_id)
