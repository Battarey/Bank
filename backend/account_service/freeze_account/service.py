"""Бизнес-логика заморозки и разморозки банковского счёта."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.rabbitmq.client import publish
from shared.rabbitmq.constants import NOTIFICATIONS_EXCHANGE, EMAIL_ROUTING_KEY, LOGS_EXCHANGE, LOG_ACCOUNT_KEY
from account_service.exceptions import (
	AccountAlreadyFrozen,
	AccountNotFound,
	AccountNotFrozen,
	AccountNotOpen,
	UnfreezeNotAllowed,
)

logger = logging.getLogger("account_service")


# ── Уведомления ────────────────────────────────────────────────────────

async def _notify_frozen(
	session: AsyncSession,
	user_id: UUID,
	account: models.BankAccount,
	frozen_by: str,
	reason: str,
) -> None:
	"""Отправляет email-уведомление о заморозке счёта."""

	contact = await session.get(models.Contact, user_id)
	if not contact:
		return

	await publish(
		exchange_name=NOTIFICATIONS_EXCHANGE,
		routing_key=EMAIL_ROUTING_KEY,
		body={
			"type": "account_frozen",
			"payload": {
				"to": contact.email,
				"variables": {
					"account_number": account.account_number,
					"frozen_by": frozen_by,
					"reason": reason,
				},
			},
		},
	)


async def _notify_unfrozen(
	session: AsyncSession,
	user_id: UUID,
	account: models.BankAccount,
) -> None:
	"""Отправляет email-уведомление о разморозке счёта."""

	contact = await session.get(models.Contact, user_id)
	if not contact:
		return

	await publish(
		exchange_name=NOTIFICATIONS_EXCHANGE,
		routing_key=EMAIL_ROUTING_KEY,
		body={
			"type": "account_unfrozen",
			"payload": {
				"to": contact.email,
				"variables": {
					"account_number": account.account_number,
				},
			},
		},
	)


# ── Операции ───────────────────────────────────────────────────────────

async def freeze_account(
	session: AsyncSession,
	user_id: UUID,
	account_id: UUID,
	*,
	frozen_by: str = "user",
	reason: str = "Заморозка по запросу пользователя",
) -> models.BankAccount:
	"""Замораживает банковский счёт.

	1. Проверяет принадлежность и текущий статус.
	2. Переводит status → frozen, сохраняет frozen_by / frozen_at / freeze_reason.
	3. Отправляет email-уведомление.
	"""

	stmt = (
		select(models.BankAccount)
		.where(models.BankAccount.id == account_id)
		.with_for_update()
	)
	result = await session.execute(stmt)
	account = result.scalar_one_or_none()

	if account is None or account.client_id != user_id:
		raise AccountNotFound("Счёт не найден.")

	if account.status == "frozen":
		raise AccountAlreadyFrozen("Счёт уже заморожен.")

	if account.status != "open":
		raise AccountNotOpen(
			f"Невозможно заморозить счёт со статусом «{account.status}»."
		)

	now = datetime.now(UTC)
	account.status = "frozen"
	account.frozen_by = frozen_by
	account.frozen_at = now
	account.freeze_reason = reason

	try:
		await session.commit()
		await session.refresh(account)
	except Exception:
		await session.rollback()
		raise

	logger.info(
		"Счёт заморожен: account=%s, frozen_by=%s, reason=%s",
		account_id, frozen_by, reason,
	)

	try:
		await _notify_frozen(session, user_id, account, frozen_by, reason)
	except Exception:
		logger.exception("Не удалось отправить уведомление о заморозке (account=%s)", account_id)

	try:
		await publish(
			exchange_name=LOGS_EXCHANGE,
			routing_key=LOG_ACCOUNT_KEY,
			body={
				"type": "account",
				"payload": {
					"user_id": str(user_id),
					"action": "freeze_account",
					"service": "account_service",
					"entity_id": str(account.id),
					"entity_type": "bank_account",
					"status": "success",
					"details": f"Заморозка счёта {account.account_number} ({frozen_by}: {reason})",
				},
			},
		)
	except Exception:
		logger.exception("Не удалось отправить лог о заморозке (account=%s)", account_id)

	return account


async def unfreeze_account(
	session: AsyncSession,
	user_id: UUID,
	account_id: UUID,
) -> models.BankAccount:
	"""Размораживает банковский счёт (только если frozen_by=user).

	1. Проверяет принадлежность и текущий статус.
	2. Проверяет, что заморозка была инициирована пользователем.
	3. Переводит status → open, очищает frozen-поля.
	4. Отправляет email-уведомление.
	"""

	stmt = (
		select(models.BankAccount)
		.where(models.BankAccount.id == account_id)
		.with_for_update()
	)
	result = await session.execute(stmt)
	account = result.scalar_one_or_none()

	if account is None or account.client_id != user_id:
		raise AccountNotFound("Счёт не найден.")

	if account.status != "frozen":
		raise AccountNotFrozen("Счёт не заморожен.")

	if account.frozen_by != "user":
		raise UnfreezeNotAllowed(
			"Счёт заморожен системой безопасности. "
			"Обратитесь в поддержку для разморозки."
		)

	account.status = "open"
	account.frozen_by = None
	account.frozen_at = None
	account.freeze_reason = None

	try:
		await session.commit()
		await session.refresh(account)
	except Exception:
		await session.rollback()
		raise

	logger.info("Счёт разморожен: account=%s", account_id)

	try:
		await _notify_unfrozen(session, user_id, account)
	except Exception:
		logger.exception("Не удалось отправить уведомление о разморозке (account=%s)", account_id)

	try:
		await publish(
			exchange_name=LOGS_EXCHANGE,
			routing_key=LOG_ACCOUNT_KEY,
			body={
				"type": "account",
				"payload": {
					"user_id": str(user_id),
					"action": "unfreeze_account",
					"service": "account_service",
					"entity_id": str(account.id),
					"entity_type": "bank_account",
					"status": "success",
					"details": f"Разморозка счёта {account.account_number}",
				},
			},
		)
	except Exception:
		logger.exception("Не удалось отправить лог о разморозке (account=%s)", account_id)

	return account


async def cascade_freeze(
	session: AsyncSession,
	user_id: UUID,
	*,
	reason: str = "Блокировка аккаунта",
) -> int:
	"""Замораживает все open-счета пользователя (системная каскадная заморозка).

	Возвращает количество замороженных счетов.
	Счета, уже замороженные пользователем (frozen_by=user), не трогает.
	"""

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

	now = datetime.now(UTC)
	count = 0
	for acc in accounts:
		acc.status = "frozen"
		acc.frozen_by = "system"
		acc.frozen_at = now
		acc.freeze_reason = reason
		count += 1

	if count:
		try:
			await session.commit()
		except Exception:
			await session.rollback()
			raise

	logger.info("Каскадная заморозка: user=%s, accounts=%d", user_id, count)
	return count


async def cascade_unfreeze(
	session: AsyncSession,
	user_id: UUID,
) -> int:
	"""Размораживает все системно-замороженные счета пользователя.

	Снимает только frozen_by=system. Пользовательские заморозки остаются.
	Возвращает количество размороженных счетов.
	"""

	stmt = (
		select(models.BankAccount)
		.where(
			models.BankAccount.client_id == user_id,
			models.BankAccount.status == "frozen",
			models.BankAccount.frozen_by == "system",
		)
		.with_for_update()
	)
	result = await session.execute(stmt)
	accounts = result.scalars().all()

	count = 0
	for acc in accounts:
		acc.status = "open"
		acc.frozen_by = None
		acc.frozen_at = None
		acc.freeze_reason = None
		count += 1

	if count:
		try:
			await session.commit()
		except Exception:
			await session.rollback()
			raise

	logger.info("Каскадная разморозка: user=%s, accounts=%d", user_id, count)
	return count
