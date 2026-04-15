from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from shared import models
from shared.events.base import LogEvent, NotificationEvent

# Обновленные импорты
from ..core.exceptions import (
	AccountFrozen,
	AccountNotFound,
	AccountNotOpen,
	InsufficientFunds,
	SecurityViolation,
	TransactionConflict,
)
from ..core.uow import TransactionUnitOfWork
from ..core.utils import apply_security_freeze, ensure_account_ownership


async def withdraw(
	uow: TransactionUnitOfWork,
	user_id: UUID,
	account_id: UUID,
	amount: Decimal,
	description: str | None,
	idempotency_key: UUID | None = None,
) -> models.Transaction:
	"""Выполняет снятие (списание) средств со счёта.

	Включает AML-проверку (Unit of Work). В случае подозрительной активности счёт блокируется.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		user_id: ID владельца.
		account_id: ID счёта.
		amount: Сумма снятия.
		description: Комментарий к операции.

	Returns:
		models.Transaction: Запись о транзакции списания.

	Raises:
		AccountNotFound: Если счёт не найден или не принадлежит пользователю.
		AccountFrozen: Если счёт заморожен.
		AccountNotOpen: Если счёт не активен.
		SecurityViolation: Если операция отклонена антифрод-системой.
		InsufficientFunds: Если на балансе недостаточно средств.
		TransactionConflict: При системных ошибках записи в БД.
	"""
	async with uow:
		# 0. Проверка идемпотентности
		if idempotency_key:
			existing = await uow.transactions.get_by_idempotency_key(idempotency_key)
			if existing:
				return existing

		# 1. Блокировка счёта
		account = await uow.transactions.get_account_for_update(account_id)

		await ensure_account_ownership(account, user_id)

		if account.status == "frozen":
			raise AccountFrozen(f"Счёт {account.account_number} заморожен.")
		if account.status != "open":
			raise AccountNotOpen(f"Счёт {account.account_number} не активен ({account.status}).")

		# 2. Антифрод-проверка
		from ..clients import security as security_client

		is_safe, violations = await security_client.check_transaction(
			account_id, "withdrawal", amount, account.currency
		)
		if not is_safe:
			await apply_security_freeze(uow, account, violations)

		# 3. Проверка баланса
		if account.balance < amount:
			raise InsufficientFunds(f"Недостаточно средств. Доступно: {account.balance} {account.currency}.")

		# 4. Обновление баланса
		balance_before = account.balance
		account.balance -= amount
		balance_after = account.balance

		# 5. Создание транзакции
		now = datetime.now(UTC)
		tx = models.Transaction(
			id=uuid4(),
			account_id=account_id,
			type="withdrawal",
			amount=amount,
			created_at=now,
			description=description or "Снятие средств",
			related_account_id=None,
			direction="outgoing",
			status="posted",
			balance_before=balance_before,
			balance_after=balance_after,
			external_ref=None,
			idempotency_key=idempotency_key,
		)
		await uow.transactions.add(tx)

		# 6. Регистрация событий в UoW (ДО коммита для авто-публикации)
		contact = await uow.transactions.get_owner_contact(user_id)
		if contact:
			uow.add_event(
				NotificationEvent(
					type="transaction_withdrawal",
					to=contact.email,
					variables={
						"account_number": account.account_number,
						"amount": str(amount),
						"currency": account.currency,
						"balance_after": str(balance_after),
					},
				)
			)

		uow.add_event(
			LogEvent(
				user_id=user_id,
				action="withdrawal",
				service="transaction_service",
				details=f"Снятие со счёта {account.account_number}",
				entity_id=tx.id,
				amount=float(amount),
				currency=account.currency,
			)
		)

		try:
			await uow.commit()
		except IntegrityError as exc:
			raise TransactionConflict("Ошибка при списании средств. Попробуйте снова.") from exc

		await uow.transactions.refresh(tx)

		return tx
