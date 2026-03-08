"""Бизнес-логика удаления (soft delete) аккаунта пользователя."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.rabbitmq.client import publish
from shared.rabbitmq.constants import (
	LOGS_EXCHANGE,
	LOG_AUTH_KEY,
	NOTIFICATIONS_EXCHANGE,
	EMAIL_ROUTING_KEY,
)


class DeleteAccountError(Exception):
	"""Базовая ошибка удаления аккаунта."""


class DeleteAccountNotFound(DeleteAccountError):
	"""Пользователь не найден."""


class DeleteAccountAlreadyDeleted(DeleteAccountError):
	"""Аккаунт уже удалён."""


async def delete_account(session: AsyncSession, user_id: UUID) -> None:
	"""Soft delete аккаунта пользователя.

	1. user.status → "deleted", updated_at → now
	2. Каскадная заморозка всех open-счетов (frozen_by=system)
	3. Email-уведомление
	4. Аудит-лог

	Отзыв сессий (revoke_all) выполняется на уровне gateway.
	"""

	user = await session.get(models.User, user_id)
	if user is None:
		raise DeleteAccountNotFound("Пользователь не найден.")
	if user.status == "deleted":
		raise DeleteAccountAlreadyDeleted("Аккаунт уже удалён.")

	now = datetime.now(UTC)

	# 1. Статус → deleted
	user.status = "deleted"
	user.updated_at = now

	# 2. Каскадная заморозка open-счетов
	stmt = (
		select(models.BankAccount)
		.where(
			models.BankAccount.client_id == user_id,
			models.BankAccount.status == "open",
		)
		.with_for_update()
	)
	result = await session.execute(stmt)
	accounts = result.scalars().all()

	for acc in accounts:
		acc.status = "frozen"
		acc.frozen_by = "system"
		acc.frozen_at = now
		acc.freeze_reason = "Удаление аккаунта"

	try:
		await session.commit()
	except Exception:
		await session.rollback()
		raise

	# 3. Email-уведомление
	contact = await session.get(models.Contact, user_id)
	if contact:
		try:
			await publish(
				exchange_name=NOTIFICATIONS_EXCHANGE,
				routing_key=EMAIL_ROUTING_KEY,
				body={
					"type": "account_deleted",
					"payload": {
						"to": contact.email,
						"variables": {},
					},
				},
			)
		except Exception:
			pass

	# 4. Аудит-лог
	try:
		await publish(
			exchange_name=LOGS_EXCHANGE,
			routing_key=LOG_AUTH_KEY,
			body={
				"type": "auth",
				"payload": {
					"user_id": str(user_id),
					"action": "delete_account",
					"service": "customer_service",
					"entity_type": "user",
					"status": "success",
					"details": "Аккаунт удалён (soft delete)",
				},
			},
		)
	except Exception:
		pass