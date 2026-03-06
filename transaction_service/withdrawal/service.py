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
from shared.rabbitmq.constants import NOTIFICATIONS_EXCHANGE, EMAIL_ROUTING_KEY, LOGS_EXCHANGE, LOG_TRANSACTION_KEY
from transaction_service.exceptions import (
	AccountFrozen,
	AccountNotFound,
	AccountNotOpen,
	InsufficientFunds,
	SecurityViolation,
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


async def _notify_security_freeze(
	session: AsyncSession,
	user_id: UUID,
	account: models.BankAccount,
	rules: str,
) -> None:
	"""Отправляет email-уведомление о заморозке счёта по AML-правилам."""

	contact = await session.get(models.Contact, user_id)
	if not contact:
		return

	await publish(
		exchange_name=NOTIFICATIONS_EXCHANGE,
		routing_key=EMAIL_ROUTING_KEY,
		body={
			"type": "security_freeze",
			"payload": {
				"to": contact.email,
				"variables": {
					"account_number": account.account_number,
					"rule": rules,
					"details": "Операция отклонена автоматической системой безопасности.",
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

	if account.status == "frozen":
		raise AccountFrozen("Счёт заморожен — исходящие операции запрещены.")

	if account.status != "open":
		raise AccountNotOpen(f"Счёт в статусе «{account.status}» — снятие невозможно.")

	# 2. AML-проверка через Security Service
	from transaction_service import security_client
	allowed, violations = await security_client.check_transaction(
		account_id, "withdrawal", amount, account.currency,
	)
	if not allowed:
		# Автозаморозка счёта
		account.status = "frozen"
		account.frozen_by = "system"
		account.frozen_at = datetime.now(UTC)
		account.freeze_reason = ", ".join(v["rule"] for v in violations)
		try:
			await session.commit()
			await session.refresh(account)
		except Exception:
			await session.rollback()
			raise
		rules = account.freeze_reason

		# Уведомление о заморозке по результатам AML
		await _notify_security_freeze(session, account.client_id, account, rules)

		raise SecurityViolation(
			f"Операция отклонена системой безопасности. Счёт заморожен. Правила: {rules}"
		)

	# 3. Проверяем баланс
	if account.balance < amount:
		raise InsufficientFunds(
			f"Недостаточно средств. Доступно: {account.balance} {account.currency}."
		)

	# 4. Обновляем баланс
	balance_before = account.balance
	balance_after = balance_before - amount
	account.balance = balance_after

	# 5. Создаём транзакцию
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

	try:
		await publish(
			exchange_name=LOGS_EXCHANGE,
			routing_key=LOG_TRANSACTION_KEY,
			body={
				"type": "transaction",
				"payload": {
					"user_id": str(user_id),
					"action": "withdrawal",
					"service": "transaction_service",
					"entity_id": str(tx.id),
					"entity_type": "transaction",
					"amount": str(amount),
					"currency": account.currency,
					"status": "success",
					"details": f"Снятие со счёта {account.account_number}",
				},
			},
		)
	except Exception:
		logger.exception("Не удалось отправить лог о снятии (account=%s)", account_id)

	return tx
