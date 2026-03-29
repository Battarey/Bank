"""Бизнес-логика удаления (soft delete) аккаунта пользователя."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.rabbitmq.client import publish
from shared.rabbitmq.constants import (
	EMAIL_ROUTING_KEY,
	LOG_AUTH_KEY,
	NOTIFICATIONS_EXCHANGE,
)
from shared.utils.log_event import log_event

from ..repository import CustomerRepository
from ..exceptions import (
	AccountAlreadyDeleted,
	AccountNotFound,
)


async def delete_account(session: AsyncSession, user_id: UUID) -> None:
	"""Выполняет мягкое удаление аккаунта клиента.

	Процесс включает:
	1. Перевод статуса пользователя в 'deleted'.
	2. Заморозку всех открытых счетов клиента.
	3. Отправку уведомления на Email.
	4. Запись события в аудит-лог.

	Args:
		session: Асинхронная сессия базы данных.
		user_id: Идентификатор удаляемого пользователя.

	Raises:
		AccountNotFound: Если пользователь не найден.
		AccountAlreadyDeleted: Если статус пользователя уже 'deleted'.
	"""
	repo = CustomerRepository(session)
	user = await repo.get(user_id)
	
	if user is None:
		raise AccountNotFound(f"Пользователь {user_id} не найден.")
	if user.status == "deleted":
		raise AccountAlreadyDeleted("Аккаунт уже был удалён ранее.")

	now = datetime.now(UTC)

	# 1. Помечаем пользователя как удаленного
	user.status = "deleted"
	user.updated_at = now

	# 2. Замораживаем все открытые счета
	accounts = await repo.get_open_accounts(user_id)
	for acc in accounts:
		acc.status = "frozen"
		acc.frozen_by = "system"
		acc.frozen_at = now
		acc.freeze_reason = "Удаление аккаунта пользователя"

	try:
		await repo.commit()
	except Exception:
		await repo.rollback()
		raise

	# 3. Отправляем уведомление (Best effort)
	contact = await repo.get_contact(user_id)
	if contact:
		try:
			await publish(
				exchange_name=NOTIFICATIONS_EXCHANGE,
				routing_key=EMAIL_ROUTING_KEY,
				body={
					"type": "account_deleted",
					"payload": {
						"to": contact.email,
						"variables": {"user_id": str(user_id)},
					},
				},
			)
		except Exception:
			pass

	# 4. Логируем событие
	await log_event(
		routing_key=LOG_AUTH_KEY,
		event_type="auth",
		payload={
			"user_id": str(user_id),
			"action": "delete_account",
			"service": "customer_service",
			"status": "success",
			"details": "Soft delete аккаунта завершен",
		}
	)