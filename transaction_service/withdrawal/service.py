"""Бизнес-логика снятия средств с банковского счёта."""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.rabbitmq.client import publish
from shared.rabbitmq.constants import NOTIFICATIONS_EXCHANGE, EMAIL_ROUTING_KEY
from transaction_service.exceptions import (
	AccountNotFound,
	AccountNotOpen,
	InsufficientFunds,
	TransactionConflict,
)

logger = logging.getLogger("transaction_service")


async def _notify_withdrawal(
	session: AsyncSession,
	user_id: UUID,
	account: models.BankAccount,
	amount: Decimal,
	balance_after: Decimal,
) -> None:
	"""Отправляет email-уведомление о снятии."""

	contact = await session.get(models.Contact, user_id)
	if not contact:
		return

	await publish(
		exchange_name=NOTIFICATIONS_EXCHANGE,
		routing_key=EMAIL_ROUTING_KEY,
		body={
			"type": "transaction_withdrawal",
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


async def withdraw(
	session: AsyncSession,
	user_id: UUID,
	account_id: UUID,
	amount: Decimal,
	description: str | None,
) -> models.Transaction:
	"""Снимает средства с банковского счёта.

	1. Проверяет принадлежность и статус.
	2. Проверяет достаточность средств.
	3. Обновляет баланс.
	4. Создаёт запись транзакции.
	"""

	# 1. Получаем счёт с блокировкой строки
	stmt = (
		select(models.BankAccount)
		.where(models.BankAccount.id == account_id)
		.with_for_update()
	)
	result = await session.execute(stmt)
	account = result.scalar_one_or_none()

	if account is None or account.client_id != user_id:
		raise AccountNotFound("Счёт не найден.")

	if account.status != "open":
		raise AccountNotOpen(f"Счёт в статусе «{account.status}» — снятие невозможно.")

	# 2. Проверяем баланс
	if account.balance < amount:
		raise InsufficientFunds(
			f"Недостаточно средств. Доступно: {account.balance} {account.currency}."
		)

	# 3. Обновляем баланс
	balance_before = account.balance
	balance_after = balance_before - amount
	account.balance = balance_after

	# 4. Создаём транзакцию
	now = datetime.now(UTC)
	tx = models.Transaction(
		id=uuid4(),
		account_id=account_id,
		type="withdrawal",
		amount=amount,
		created_at=now,
		description=description,
		related_account_id=None,
		direction="outgoing",
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
		"Снятие: account=%s, amount=%s %s, balance=%s",
		account_id, amount, account.currency, balance_after,
	)

	try:
		await _notify_withdrawal(session, user_id, account, amount, balance_after)
	except Exception:
		logger.exception("Не удалось отправить уведомление о снятии (account=%s)", account_id)

	return tx
