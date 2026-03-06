"""Бизнес-логика пополнения банковского счёта."""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.rabbitmq.client import publish
from shared.rabbitmq.constants import NOTIFICATIONS_EXCHANGE, EMAIL_ROUTING_KEY, LOGS_EXCHANGE, LOG_TRANSACTION_KEY
from transaction_service.exceptions import (
	AccountNotFound,
	AccountNotOpen,
	TransactionConflict,
)

logger = logging.getLogger("transaction_service")

# Мягкая заморозка: пополнение разрешено на open и frozen счетах
_DEPOSIT_ALLOWED_STATUSES = {"open", "frozen"}


async def _notify_deposit(
	session: AsyncSession,
	user_id: UUID,
	account: models.BankAccount,
	amount: Decimal,
	balance_after: Decimal,
) -> None:
	"""Отправляет email-уведомление о пополнении."""

	contact = await session.get(models.Contact, user_id)
	if not contact:
		return

	await publish(
		exchange_name=NOTIFICATIONS_EXCHANGE,
		routing_key=EMAIL_ROUTING_KEY,
		body={
			"type": "transaction_deposit",
			"payload": {
				"to": contact.email,
				"variables": {
					"account_number": account.account_number,
					"amount": str(amount),
					"currency": account.currency,
					"balance_after": str(balance_after),
				},
			},
		},
	)


async def deposit(
	session: AsyncSession,
	user_id: UUID,
	account_id: UUID,
	amount: Decimal,
	description: str | None,
) -> models.Transaction:
	"""Пополняет банковский счёт.

	1. Проверяет принадлежность и статус счёта.
	2. Обновляет баланс.
	3. Создаёт запись транзакции.
	"""

	# 1. Получаем счёт с блокировкой строки (FOR UPDATE)
	stmt = (
		select(models.BankAccount)
		.where(models.BankAccount.id == account_id)
		.with_for_update()
	)
	result = await session.execute(stmt)
	account = result.scalar_one_or_none()

	if account is None or account.client_id != user_id:
		raise AccountNotFound("Счёт не найден.")

	if account.status not in _DEPOSIT_ALLOWED_STATUSES:
		raise AccountNotOpen(f"Счёт в статусе «{account.status}» — пополнение невозможно.")

	# 2. Обновляем баланс
	balance_before = account.balance
	balance_after = balance_before + amount
	account.balance = balance_after

	# 3. Создаём транзакцию
	now = datetime.now(UTC)
	tx = models.Transaction(
		id=uuid4(),
		account_id=account_id,
		type="deposit",
		amount=amount,
		created_at=now,
		description=description,
		related_account_id=None,
		direction="incoming",
		status="posted",
		balance_before=balance_before,
		balance_after=balance_after,
		external_ref=None,
	)
	session.add(tx)

	try:
		await session.commit()
		await session.refresh(tx)
		await session.refresh(account)
	except IntegrityError:
		await session.rollback()
		raise TransactionConflict("Конфликт при проведении операции. Попробуйте снова.")

	logger.info(
		"Пополнение: account=%s, amount=%s %s, balance=%s",
		account_id, amount, account.currency, balance_after,
	)

	try:
		await _notify_deposit(session, user_id, account, amount, balance_after)
	except Exception:
		logger.exception("Не удалось отправить уведомление о пополнении (account=%s)", account_id)

	try:
		await publish(
			exchange_name=LOGS_EXCHANGE,
			routing_key=LOG_TRANSACTION_KEY,
			body={
				"type": "transaction",
				"payload": {
					"user_id": str(user_id),
					"action": "deposit",
					"service": "transaction_service",
					"entity_id": str(tx.id),
					"entity_type": "transaction",
					"amount": str(amount),
					"currency": account.currency,
					"status": "success",
					"details": f"Пополнение счёта {account.account_number}",
				},
			},
		)
	except Exception:
		logger.exception("Не удалось отправить лог о пополнении (account=%s)", account_id)

	return tx
