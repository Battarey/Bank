"""Бизнес-логика переводов между счетами внутри банка."""

import logging
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
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
	RateUnavailable,
	SameAccountTransfer,
	SecurityViolation,
	TransactionConflict,
)

logger = logging.getLogger("transaction_service")

# Мягкая заморозка: входящие переводы разрешены на frozen-счета
_RECEIVE_ALLOWED_STATUSES = {"open", "frozen"}


async def _notify_transfer(
	session: AsyncSession,
	user_id: UUID,
	from_account: models.BankAccount,
	to_account: models.BankAccount,
	amount: Decimal,
	balance_after: Decimal,
	converted_amount: Decimal | None = None,
	rate: Decimal | None = None,
) -> None:
	"""Уведомление отправителю о переводе."""

	contact = await session.get(models.Contact, user_id)
	if not contact:
		return

	if converted_amount is not None and rate is not None:
		amount_text = (
			f"{amount} {from_account.currency} → "
			f"{converted_amount} {to_account.currency} (курс {rate})"
		)
	else:
		amount_text = str(amount)

	await publish(
		exchange_name=NOTIFICATIONS_EXCHANGE,
		routing_key=EMAIL_ROUTING_KEY,
		body={
			"type": "transaction_transfer",
			"payload": {
				"to": contact.email,
				"variables": {
					"from_account": from_account.account_number,
					"to_account": to_account.account_number,
					"amount": amount_text,
					"currency": from_account.currency,
					"balance_after": str(balance_after),
				},
			},
		},
	)


async def _notify_incoming_transfer(
	session: AsyncSession,
	to_account: models.BankAccount,
	from_account: models.BankAccount,
	amount: Decimal,
	balance_after: Decimal,
	original_amount: Decimal | None = None,
	rate: Decimal | None = None,
) -> None:
	"""Уведомление получателю о входящем переводе."""

	contact = await session.get(models.Contact, to_account.client_id)
	if not contact:
		return

	if original_amount is not None and rate is not None:
		amount_text = (
			f"{original_amount} {from_account.currency} → "
			f"{amount} {to_account.currency} (курс {rate})"
		)
	else:
		amount_text = str(amount)

	await publish(
		exchange_name=NOTIFICATIONS_EXCHANGE,
		routing_key=EMAIL_ROUTING_KEY,
		body={
			"type": "transaction_incoming",
			"payload": {
				"to": contact.email,
				"variables": {
					"account_number": to_account.account_number,
					"from_account": from_account.account_number,
					"amount": amount_text,
					"currency": to_account.currency,
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


async def transfer(
	session: AsyncSession,
	user_id: UUID,
	from_account_id: UUID,
	to_account_id: UUID,
	amount: Decimal,
	description: str | None,
) -> models.Transaction:
	"""Перевод между счетами внутри банка.

	Поддерживает перевод между своими счетами и на счёт другого клиента.
	1. Блокирует оба счёта (в порядке UUID для предотвращения deadlock).
	2. Проверяет принадлежность счёта-отправителя, статусы, валюту, баланс.
	3. Обновляет балансы обоих счетов.
	4. Создаёт две записи транзакций (outgoing + incoming).
	"""

	if from_account_id == to_account_id:
		raise SameAccountTransfer("Перевод на тот же счёт невозможен.")

	# 1. Блокируем оба счёта (order by UUID для избежания deadlock)
	ordered_ids = sorted([from_account_id, to_account_id])
	stmt = (
		select(models.BankAccount)
		.where(models.BankAccount.id.in_(ordered_ids))
		.with_for_update()
		.order_by(models.BankAccount.id)
	)
	result = await session.execute(stmt)
	accounts = {acc.id: acc for acc in result.scalars().all()}

	from_account = accounts.get(from_account_id)
	to_account = accounts.get(to_account_id)

	# 2. Проверки
	if from_account is None or from_account.client_id != user_id:
		raise AccountNotFound("Счёт-отправитель не найден.")

	if to_account is None:
		raise AccountNotFound("Счёт-получатель не найден.")

	if from_account.status == "frozen":
		raise AccountFrozen("Счёт-отправитель заморожен — исходящие операции запрещены.")

	if from_account.status != "open":
		raise AccountNotOpen(f"Счёт-отправитель в статусе «{from_account.status}».")

	if to_account.status not in _RECEIVE_ALLOWED_STATUSES:
		raise AccountNotOpen(f"Счёт-получатель в статусе «{to_account.status}».")

	if from_account.balance < amount:
		raise InsufficientFunds(
			f"Недостаточно средств. Доступно: {from_account.balance} {from_account.currency}."
		)

	# Конвертация валюты (если валюты различаются)
	cross_currency = from_account.currency != to_account.currency
	rate: Decimal | None = None
	credited_amount = amount  # сумма зачисления в валюте получателя

	if cross_currency:
		from transaction_service import currency_client
		try:
			rate = await currency_client.get_rate(from_account.currency, to_account.currency)
		except Exception as exc:
			logger.exception(
				"Ошибка получения курса %s→%s", from_account.currency, to_account.currency,
			)
			raise RateUnavailable(
				f"Не удалось получить курс {from_account.currency}/{to_account.currency}: {exc}"
			) from exc
		credited_amount = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

	# AML-проверка через Security Service
	from transaction_service import security_client
	allowed, violations = await security_client.check_transaction(
		from_account_id, "transfer", amount, from_account.currency,
	)
	if not allowed:
		from_account.status = "frozen"
		from_account.frozen_by = "system"
		from_account.frozen_at = datetime.now(UTC)
		from_account.freeze_reason = ", ".join(v["rule"] for v in violations)
		try:
			await session.commit()
			await session.refresh(from_account)
		except Exception:
			await session.rollback()
			raise
		rules = from_account.freeze_reason

		# Уведомление о заморозке по результатам AML
		await _notify_security_freeze(session, user_id, from_account, rules)

		raise SecurityViolation(
			f"Операция отклонена системой безопасности. Счёт заморожен. Правила: {rules}"
		)

	# 3. Обновляем балансы
	now = datetime.now(UTC)

	from_balance_before = from_account.balance
	from_balance_after = from_balance_before - amount
	from_account.balance = from_balance_after

	to_balance_before = to_account.balance
	to_balance_after = to_balance_before + credited_amount
	to_account.balance = to_balance_after

	# 4. Создаём транзакции (outgoing для отправителя, incoming для получателя)
	tx_description = description
	if cross_currency:
		tx_description = (
			f"{description or 'Перевод'} "
			f"({from_account.currency}→{to_account.currency}, курс {rate})"
		)

	tx_out = models.Transaction(
		id=uuid4(),
		account_id=from_account_id,
		type="transfer",
		amount=amount,
		created_at=now,
		description=tx_description,
		related_account_id=to_account_id,
		direction="outgoing",
		status="posted",
		balance_before=from_balance_before,
		balance_after=from_balance_after,
		external_ref=str(rate) if cross_currency else None,
	)

	tx_in = models.Transaction(
		id=uuid4(),
		account_id=to_account_id,
		type="transfer",
		amount=credited_amount,
		created_at=now,
		description=tx_description,
		related_account_id=from_account_id,
		direction="incoming",
		status="posted",
		balance_before=to_balance_before,
		balance_after=to_balance_after,
		external_ref=str(rate) if cross_currency else None,
	)

	session.add_all([tx_out, tx_in])

	try:
		await session.commit()
		await session.refresh(tx_out)
		await session.refresh(from_account)
		await session.refresh(to_account)
	except IntegrityError:
		await session.rollback()
		raise TransactionConflict("Конфликт при проведении перевода. Попробуйте снова.")

	logger.info(
		"Перевод: %s → %s, amount=%s %s%s",
		from_account_id, to_account_id, amount, from_account.currency,
		f" → {credited_amount} {to_account.currency} (курс {rate})" if cross_currency else "",
	)

	try:
		await _notify_transfer(
			session, user_id, from_account, to_account, amount, from_balance_after,
			converted_amount=credited_amount if cross_currency else None,
			rate=rate,
		)
	except Exception:
		logger.exception("Не удалось отправить уведомление отправителю (account=%s)", from_account_id)

	# Уведомление получателю (если это другой клиент)
	if to_account.client_id != user_id:
		try:
			await _notify_incoming_transfer(
				session, to_account, from_account, credited_amount, to_balance_after,
				original_amount=amount if cross_currency else None,
				rate=rate,
			)
		except Exception:
			logger.exception("Не удалось отправить уведомление получателю (account=%s)", to_account_id)

	try:
		await publish(
			exchange_name=LOGS_EXCHANGE,
			routing_key=LOG_TRANSACTION_KEY,
			body={
				"type": "transaction",
				"payload": {
					"user_id": str(user_id),
					"action": "transfer",
					"service": "transaction_service",
					"entity_id": str(tx_out.id),
					"entity_type": "transaction",
					"amount": str(amount),
					"currency": from_account.currency,
					"status": "success",
					"details": (
						f"Перевод {from_account.account_number} → {to_account.account_number}"
						+ (f", {amount} {from_account.currency} → {credited_amount} {to_account.currency}, курс {rate}" if cross_currency else "")
					),
				},
			},
		)
	except Exception:
		logger.exception("Не удалось отправить лог о переводе (account=%s)", from_account_id)

	return tx_out
