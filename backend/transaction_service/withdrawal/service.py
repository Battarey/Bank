"""Бизнес-логика снятия средств с банковского счёта."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from ..uow import TransactionUnitOfWork
from ..exceptions import (
	AccountFrozen,
	AccountNotOpen,
	InsufficientFunds,
	SecurityViolation,
	TransactionConflict,
)


async def withdraw(
	uow: TransactionUnitOfWork,
	user_id: UUID,
	account_id: UUID,
	amount: Decimal,
	description: str | None,
) -> models.Transaction:
	"""Выполняет снятие (списание) средств со счёта.

	Включает AML-проверку (Unit of Work). В случае подозрительной активности счёт блокируется.

	Args:
		uow: Unit of Work для управления транзакцией.
		user_id: ID владельца.
		account_id: ID счёта.
		amount: Сумма снятия.
		description: Комментарий.

	Returns:
		Transaction: Запись о транзакции списания.
	"""
	async with uow:
		# 1. Блокировка счёта
		account = await uow.transactions.get_account_for_update(account_id)
		
		if account.client_id != user_id:
			from ..exceptions import AccountNotFound
			raise AccountNotFound("Счёт не принадлежит вам.")

		if account.status == "frozen":
			raise AccountFrozen(f"Счёт {account.account_number} заморожен.")
		if account.status != "open":
			raise AccountNotOpen(f"Счёт {account.account_number} не активен ({account.status}).")

		# 2. Антифрод-проверка
		from .. import security_client
		is_safe, violations = await security_client.check_transaction(
			account_id, "withdrawal", amount, account.currency
		)
		if not is_safe:
			reason = ", ".join(v["rule"] for v in violations)
			account.status = "frozen"
			account.frozen_by = "system"
			account.frozen_at = datetime.now(UTC)
			account.freeze_reason = f"AML: {reason}"
			await uow.commit() # Сохраняем блокировку даже при нарушении правил
			
			# Уведомление о блокировке
			from ..history.service import _notify_security_freeze
			await _notify_security_freeze(uow.transactions, user_id, account, reason)
			
			raise SecurityViolation(f"Операция отклонена безопасностью. Счёт заморожен: {reason}")

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
		)
		await uow.transactions.add(tx)

		try:
			await uow.commit()
		except IntegrityError as exc:
			raise TransactionConflict("Ошибка при списании средств. Попробуйте снова.") from exc

		await uow.transactions.refresh(tx)

		# Уведомление на Email (best effort)
		contact = await uow.transactions.get_owner_contact(user_id)
		if contact:
			try:
				await send_notification(
					notification_type="transaction_withdrawal",
					to=contact.email,
					variables={
						"account_number": account.account_number,
						"amount": str(amount),
						"currency": account.currency,
						"balance_after": str(balance_after),
					},
				)
			except Exception:
				pass

		await send_log(
			routing_key=LOG_TRANSACTION_KEY,
			user_id=user_id,
			action="withdrawal",
			service="transaction_service",
			details=f"Снятие со счёта {account.account_number}",
			entity_id=str(tx.id),
			amount=str(amount),
			currency=account.currency,
		)

		return tx
