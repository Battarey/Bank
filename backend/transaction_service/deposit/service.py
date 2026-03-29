"""Бизнес-логика пополнения банковского счёта."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.rabbitmq.client import publish
from shared.rabbitmq.constants import (
	EMAIL_ROUTING_KEY,
	LOG_TRANSACTION_KEY,
	NOTIFICATIONS_EXCHANGE,
)
from shared.utils.log_event import log_event

from ..repository import TransactionRepository
from ..exceptions import (
	AccountNotOpen,
	TransactionConflict,
)

# Мягкая заморозка: пополнение разрешено на open и frozen счетах
_DEPOSIT_ALLOWED_STATUSES = {"open", "frozen"}


async def deposit(
	session: AsyncSession,
	user_id: UUID,
	account_id: UUID,
	amount: Decimal,
	description: str | None,
) -> models.Transaction:
	"""Пополняет баланс банковского счёта.

	Операция разрешена как для активных, так и для замороженных счетов.

	Args:
		session: Сессия БД.
		user_id: ID владельца счёта.
		account_id: ID пополняемого счёта.
		amount: Сумма пополнения.
		description: Комментарий к операции.

	Returns:
		Transaction: Созданная запись транзакции.

	Raises:
		AccountNotFound: Если счёт не найден или не принадлежит пользователю.
		AccountNotOpen: Если счёт закрыт.
		TransactionConflict: При ошибке записи в БД.
	"""
	repo = TransactionRepository(session)
	
	# 1. Получение счёта с блокировкой
	account = await repo.get_account_for_update(account_id)
	
	if account.client_id != user_id:
		from ..exceptions import AccountNotFound
		raise AccountNotFound("Счёт не принадлежит вам.")

	if account.status not in _DEPOSIT_ALLOWED_STATUSES:
		raise AccountNotOpen(f"Счёт {account.account_number} в статусе «{account.status}» — пополнение невозможно.")

	# 2. Обновление баланса
	balance_before = account.balance
	account.balance += amount
	balance_after = account.balance

	# 3. Создание транзакции
	now = datetime.now(UTC)
	tx = models.Transaction(
		id=uuid4(),
		account_id=account_id,
		type="deposit",
		amount=amount,
		created_at=now,
		description=description or "Пополнение счёта",
		related_account_id=None,
		direction="incoming",
		status="posted",
		balance_before=balance_before,
		balance_after=balance_after,
		external_ref=None,
	)
	await repo.add(tx)

	try:
		await repo.commit()
	except IntegrityError as exc:
		await repo.rollback()
		raise TransactionConflict("Ошибка при зачислении средств. Попробуйте снова.") from exc

	await repo.refresh(tx)

	# 4. Уведомление и логирование (Best effort)
	contact = await repo.get_owner_contact(user_id)
	if contact:
		try:
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
		except Exception:
			pass

	await log_event(
		routing_key=LOG_TRANSACTION_KEY,
		event_type="transaction",
		payload={
			"user_id": str(user_id),
			"action": "deposit",
			"service": "transaction_service",
			"entity_id": str(tx.id),
			"amount": str(amount),
			"currency": account.currency,
			"status": "success",
			"details": f"Пополнение счёта {account.account_number}",
		}
	)

	return tx
