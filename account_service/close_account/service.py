"""Бизнес-логика закрытия банковского счёта."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.rabbitmq.client import publish
from shared.rabbitmq.constants import NOTIFICATIONS_EXCHANGE, EMAIL_ROUTING_KEY
from account_service.exceptions import (
	AccountConflict,
	AccountNonZeroBalance,
	AccountNotFound,
	AccountNotOpen,
)

logger = logging.getLogger("account_service")


# ── Уведомления ────────────────────────────────────────────────────────

async def _notify_account_closed(
	session: AsyncSession,
	user_id: UUID,
	account: models.BankAccount,
) -> None:
	"""Отправляет email-уведомление о закрытии счёта."""
	contact = await session.get(models.Contact, user_id)
	if not contact:
		return
	await publish(
		exchange_name=NOTIFICATIONS_EXCHANGE,
		routing_key=EMAIL_ROUTING_KEY,
		body={
			"type": "account_closed",
			"payload": {
				"to": contact.email,
				"variables": {
					"account_number": account.account_number,
				},
			},
		},
	)


# ── Операции ───────────────────────────────────────────────────────────

async def close_account(
	session: AsyncSession,
	user_id: UUID,
	account_id: UUID,
) -> models.BankAccount:
	"""Закрывает банковский счёт (status → closed, closed_at → now).

	Предусловия:
	  - Счёт принадлежит пользователю.
	  - Статус = open.
	  - Баланс = 0.
	"""

	account = await session.get(models.BankAccount, account_id)

	# 1. Существование и принадлежность
	if account is None or account.client_id != user_id:
		raise AccountNotFound("Счёт не найден.")

	# 2. Статус
	if account.status != "open":
		raise AccountNotOpen(
			f"Невозможно закрыть счёт со статусом «{account.status}»."
		)

	# 3. Баланс
	if account.balance != 0:
		raise AccountNonZeroBalance(
			f"На счёте остаток {account.balance} {account.currency}. "
			"Переведите средства перед закрытием."
		)

	# 4. Закрываем
	account.status = "closed"
	account.closed_at = datetime.now(UTC)

	try:
		await session.commit()
		await session.refresh(account)
	except IntegrityError:
		await session.rollback()
		raise AccountConflict("Конфликт данных при закрытии счёта.")

	logger.info("Счёт закрыт: user=%s, account=%s", user_id, account_id)

	await _notify_account_closed(session, user_id, account)

	return account


__all__ = [
	"close_account",
]
