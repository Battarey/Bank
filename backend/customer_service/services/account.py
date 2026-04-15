"""Бизнес-логика удаления (soft delete) аккаунта пользователя."""

from datetime import UTC, datetime
from uuid import UUID

from shared.events.base import LogEvent, NotificationEvent

from ..core.exceptions import (
	AccountAlreadyDeleted,
	AccountNotFound,
)
from ..core.uow import CustomerUnitOfWork


async def delete_account(uow: CustomerUnitOfWork, user_id: UUID) -> None:
	"""Выполняет мягкое удаление аккаунта клиента.

	Процесс включает:
	1. Перевод статуса пользователя в 'deleted'.
	2. Заморозку всех открытых счетов клиента.
	3. Регистрацию событий для уведомления и логирования.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		user_id: Идентификатор удаляемого пользователя.

	Raises:
		AccountNotFound: Если пользователь не найден.
		AccountAlreadyDeleted: Если статус пользователя уже 'deleted'.
	"""
	async with uow:
		user = await uow.customers.get(user_id)

		if user is None:
			raise AccountNotFound(f"Пользователь {user_id} не найден.")
		if user.status == "deleted":
			raise AccountAlreadyDeleted("Аккаунт уже был удалён ранее.")

		now = datetime.now(UTC)

		# 1. Помечаем пользователя как удаленного
		user.status = "deleted"
		user.updated_at = now

		# 2. Замораживаем все открытые счета
		accounts = await uow.customers.get_open_accounts(user_id)
		for acc in accounts:
			acc.status = "frozen"
			acc.frozen_by = "system"
			acc.frozen_at = now
			acc.freeze_reason = "Удаление аккаунта пользователя"

		# 3. Регистрация событий ДО коммита
		contact = await uow.customers.get_contact(user_id)
		if contact:
			uow.add_event(
				NotificationEvent(
					type="account_deleted",
					to=contact.email,
					variables={"user_id": str(user_id)},
				)
			)

		uow.add_event(
			LogEvent(
				user_id=user_id,
				action="delete_account",
				service="customer_service",
				details="Soft delete аккаунта завершен",
			)
		)

		await uow.commit()
