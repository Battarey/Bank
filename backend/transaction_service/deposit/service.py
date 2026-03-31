from sqlalchemy.exc import IntegrityError

from shared import models
from shared.events.base import LogEvent, NotificationEvent
from ..uow import TransactionUnitOfWork
from ..exceptions import (
	AccountNotOpen,
	TransactionConflict,
)

# Мягкая заморозка: пополнение разрешено на open и frozen счетах
_DEPOSIT_ALLOWED_STATUSES = {"open", "frozen"}


async def deposit(
	uow: TransactionUnitOfWork,
	user_id: UUID,
	account_id: UUID,
	amount: Decimal,
	description: str | None,
) -> models.Transaction:
	"""Пополняет баланс банковского счёта.

	Операция разрешена как для активных, так и для замороженных счетов.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		user_id: ID владельца счёта.
		account_id: ID пополняемого счёта.
		amount: Сумма пополнения.
		description: Комментарий к операции.

	Returns:
		models.Transaction: Созданная запись транзакции.

	Raises:
		AccountNotFound: Если счёт не найден или не принадлежит пользователю.
		AccountNotOpen: Если счёт находится в статусе, не позволяющем пополнение.
		TransactionConflict: При системных ошибках записи в БД.
	"""
	async with uow:
		# 1. Получение счёта с блокировкой
		account = await uow.transactions.get_account_for_update(account_id)
		
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
		await uow.transactions.add(tx)

		# 4. Регистрация событий в UoW (ДО коммита для авто-публикации)
		contact = await uow.transactions.get_owner_contact(user_id)
		if contact:
			uow.add_event(NotificationEvent(
				type="transaction_deposit",
				to=contact.email,
				variables={
					"account_number": account.account_number,
					"amount": str(amount),
					"currency": account.currency,
					"balance_after": str(balance_after),
				},
			))

		uow.add_event(LogEvent(
			user_id=user_id,
			action="deposit",
			service="transaction_service",
			details=f"Пополнение счёта {account.account_number}",
			entity_id=tx.id,
			amount=float(amount),
			currency=account.currency,
		))

		try:
			await uow.commit()
		except IntegrityError as exc:
			raise TransactionConflict("Ошибка при зачислении средств. Попробуйте снова.") from exc

		await uow.transactions.refresh(tx)

		return tx
