"""Бизнес-логика обмена валюты между банковскими счетами (RUB/USD/EUR)."""

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
from currency_service import exchange_client
from currency_service.exceptions import (
	AccountNotFound,
	AccountNotOpen,
	InsufficientFunds,
	RateUnavailable,
	SameAccountExchange,
	SameCurrencyExchange,
)

logger = logging.getLogger("currency_service")


async def _notify_exchange(
	session: AsyncSession,
	user_id: UUID,
	from_account: models.BankAccount,
	to_account: models.BankAccount,
	from_amount: Decimal,
	to_amount: Decimal,
	rate: Decimal,
) -> None:
	"""Уведомление об обмене валюты."""
	contact = await session.get(models.Contact, user_id)
	if not contact:
		return

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
					"amount": f"{from_amount} {from_account.currency} → {to_amount} {to_account.currency}",
					"currency": from_account.currency,
					"balance_after": str(from_account.balance),
				},
			},
		},
	)


async def exchange(
	session: AsyncSession,
	user_id: UUID,
	from_account_id: UUID,
	to_account_id: UUID,
	amount: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
	"""Обменивает валюту между двумя счетами пользователя.

	Returns:
		(from_amount, to_amount, rate) — списано, зачислено, курс.
	"""
	if from_account_id == to_account_id:
		raise SameAccountExchange("Обмен на тот же счёт невозможен.")

	# 1. Блокируем оба счёта (порядок по UUID для предотвращения deadlock)
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
		raise AccountNotFound("Счёт-источник не найден.")
	if to_account is None or to_account.client_id != user_id:
		raise AccountNotFound("Счёт-назначение не найден.")

	if from_account.status != "open":
		raise AccountNotOpen(f"Счёт-источник в статусе «{from_account.status}».")
	if to_account.status != "open":
		raise AccountNotOpen(f"Счёт-назначение в статусе «{to_account.status}».")

	if from_account.currency == to_account.currency:
		raise SameCurrencyExchange("Валюты совпадают — используйте обычный перевод.")

	if from_account.balance < amount:
		raise InsufficientFunds(
			f"Недостаточно средств. Доступно: {from_account.balance} {from_account.currency}."
		)

	# 3. Получаем актуальный курс
	try:
		rate, rate_updated = await exchange_client.get_fresh_rate(
			from_account.currency, to_account.currency,
		)
	except Exception as exc:
		logger.exception("Ошибка получения курса %s→%s", from_account.currency, to_account.currency)
		raise RateUnavailable(f"Не удалось получить курс: {exc}") from exc

	# 4. Рассчитываем конвертированную сумму
	converted = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

	# 5. Обновляем балансы
	now = datetime.now(UTC)

	from_balance_before = from_account.balance
	from_balance_after = from_balance_before - amount
	from_account.balance = from_balance_after

	to_balance_before = to_account.balance
	to_balance_after = to_balance_before + converted
	to_account.balance = to_balance_after

	# 6. Создаём транзакции
	tx_out = models.Transaction(
		id=uuid4(),
		account_id=from_account_id,
		type="exchange",
		amount=amount,
		created_at=now,
		description=f"Обмен {from_account.currency}→{to_account.currency}, курс {rate}",
		related_account_id=to_account_id,
		direction="outgoing",
		status="posted",
		balance_before=from_balance_before,
		balance_after=from_balance_after,
		external_ref=str(rate),
	)

	tx_in = models.Transaction(
		id=uuid4(),
		account_id=to_account_id,
		type="exchange",
		amount=converted,
		created_at=now,
		description=f"Обмен {from_account.currency}→{to_account.currency}, курс {rate}",
		related_account_id=from_account_id,
		direction="incoming",
		status="posted",
		balance_before=to_balance_before,
		balance_after=to_balance_after,
		external_ref=str(rate),
	)

	session.add_all([tx_out, tx_in])

	try:
		await session.commit()
		await session.refresh(from_account)
		await session.refresh(to_account)
	except IntegrityError:
		await session.rollback()
		raise

	logger.info(
		"Обмен: %s %s → %s %s, курс=%s",
		amount, from_account.currency, converted, to_account.currency, rate,
	)

	try:
		await _notify_exchange(session, user_id, from_account, to_account, amount, converted, rate)
	except Exception:
		logger.exception("Не удалось отправить уведомление об обмене")

	try:
		await publish(
			exchange_name=LOGS_EXCHANGE,
			routing_key=LOG_TRANSACTION_KEY,
			body={
				"type": "transaction",
				"payload": {
					"user_id": str(user_id),
					"action": "currency_exchange",
					"service": "currency_service",
					"entity_id": str(tx_out.id),
					"entity_type": "transaction",
					"amount": str(amount),
					"currency": from_account.currency,
					"status": "success",
					"details": (
						f"Обмен {amount} {from_account.currency} → "
						f"{converted} {to_account.currency}, курс {rate}"
					),
				},
			},
		)
	except Exception:
		logger.exception("Не удалось отправить лог об обмене")

	return amount, converted, rate
