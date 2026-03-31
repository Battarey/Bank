"""Бизнес-логика переводов между счетами внутри банка."""

from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from shared import models
from shared.events.base import LogEvent, NotificationEvent
from ..uow import TransactionUnitOfWork
from ..exceptions import (
	AccountFrozen,
	AccountNotFound,
	AccountNotOpen,
	InsufficientFunds,
	RateUnavailable,
	SameAccountTransfer,
	SecurityViolation,
	TransactionConflict,
)

# Мягкая заморозка: исходящие операции запрещены, пополнение возможно.
_RECEIVE_ALLOWED_STATUSES = {"open", "frozen"}


async def transfer(
	uow: TransactionUnitOfWork,
	user_id: UUID,
	from_account_id: UUID,
	to_account_id: UUID,
	amount: Decimal,
	description: str | None,
) -> models.Transaction:
	"""Выполняет перевод средств между банковскими счетами.

	Атомарная операция (Unit of Work):
	1. Блокирует счета-участники (FOR UPDATE) для предотвращения гонок.
	2. Проверяет баланс, статус и лимиты AML.
	3. Выполняет конвертацию валют (если требуется).
	4. Создает записи транзакций для обоих участников.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		user_id: ID отправителя.
		from_account_id: Счёт списания.
		to_account_id: Счёт зачисления.
		amount: Сумма списания.
		description: Комментарий к платежу.

	Returns:
		models.Transaction: Созданная запись транзакции списания.

	Raises:
		SameAccountTransfer: Если счета списания и зачисления совпадают.
		AccountNotFound: Если один из счетов не найден или не принадлежит пользователю.
		AccountFrozen: Если счёт отправителя заморожен.
		AccountNotOpen: Если один из счетов закрыт.
		InsufficientFunds: Если на счёте отправителя недостаточно средств.
		RateUnavailable: Если произошла ошибка при конвертации валют.
		SecurityViolation: Если операция заблокирована антифрод-системой.
		TransactionConflict: При системных ошибках записи в БД.
	"""
	if from_account_id == to_account_id:
		raise SameAccountTransfer("Перевод на тот же счёт невозможен.")

	async with uow:
		# 1. Атомарная блокировка счетов
		accounts = await uow.transactions.lock_accounts([from_account_id, to_account_id])
		from_acc = accounts.get(from_account_id)
		to_acc = accounts.get(to_account_id)

		if not from_acc:
			raise AccountNotFound(f"Счёт списания {from_account_id} не найден.")
		if from_acc.client_id != user_id:
			raise AccountNotFound("Счёт не принадлежит вам.")
		if not to_acc:
			raise AccountNotFound(f"Счёт зачисления {to_account_id} не найден.")

		# 2. Проверка статусов
		if from_acc.status == "frozen":
			raise AccountFrozen(f"Счёт {from_acc.account_number} заморожен.")
		if from_acc.status != "open":
			raise AccountNotOpen(f"Счёт {from_acc.account_number} не активен ({from_acc.status}).")
		if to_acc.status not in _RECEIVE_ALLOWED_STATUSES:
			raise AccountNotOpen(f"Счёт получателя {to_acc.account_number} недоступен.")

		if from_acc.balance < amount:
			raise InsufficientFunds(f"Недостаточно средств. Доступно: {from_acc.balance} {from_acc.currency}.")

		# 3. Валютная конвертация
		cross_currency = from_acc.currency != to_acc.currency
		rate = Decimal("1.0")
		credited_amount = amount

		if cross_currency:
			from .. import currency_client
			try:
				rate = await currency_client.get_rate(from_acc.currency, to_acc.currency)
				credited_amount = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
			except Exception as exc:
				raise RateUnavailable(f"Ошибка получения курса валют: {exc}") from exc

		# 4. Антифрод-проверка
		from .. import security_client
		is_safe, violations = await security_client.check_transaction(
			from_account_id, "transfer", amount, from_acc.currency
		)
		if not is_safe:
			reason = ", ".join(v["rule"] for v in violations)
			from_acc.status = "frozen"
			from_acc.frozen_by = "system"
			from_acc.frozen_at = datetime.now(UTC)
			from_acc.freeze_reason = f"AML: {reason}"
			
			uow.add_event(NotificationEvent(
				type="security_freeze",
				to="owner", 
				variables={"account_number": from_acc.account_number, "rule": reason}
			))
			
			await uow.commit() # Сохраняем блокировку даже при нарушении правил
			
			raise SecurityViolation(f"Операция отклонена безопасностью. Счёт заморожен: {reason}")

		# 5. Выполнение проводок
		now = datetime.now(UTC)
		from_bal_before, to_bal_before = from_acc.balance, to_acc.balance
		
		from_acc.balance -= amount
		to_acc.balance += credited_amount

		tx_desc = description or "Перевод"
		if cross_currency:
			tx_desc += f" (Курс: {rate})"

		tx_out = models.Transaction(
			id=uuid4(),
			account_id=from_account_id,
			type="transfer",
			amount=amount,
			created_at=now,
			description=tx_desc,
			related_account_id=to_account_id,
			direction="outgoing",
			status="posted",
			balance_before=from_bal_before,
			balance_after=from_acc.balance,
			external_ref=str(rate) if cross_currency else None,
		)

		tx_in = models.Transaction(
			id=uuid4(),
			account_id=to_account_id,
			type="transfer",
			amount=credited_amount,
			created_at=now,
			description=tx_desc,
			related_account_id=from_account_id,
			direction="incoming",
			status="posted",
			balance_before=to_bal_before,
			balance_after=to_acc.balance,
			external_ref=str(rate) if cross_currency else None,
		)

		await uow.transactions.add_all([tx_out, tx_in])

		# 6. Регистрация событий в UoW (ДО коммита для авто-публикации)
		# Уведомление отправителю
		contact = await uow.transactions.get_owner_contact(user_id)
		if contact:
			uow.add_event(NotificationEvent(
				type="transaction_transfer",
				to=contact.email,
				variables={
					"from_account": from_acc.account_number, 
					"to_account": to_acc.account_number,
					"amount": f"{amount} {from_acc.currency}", 
					"balance_after": str(from_acc.balance)
				}
			))

		# Уведомление получателю (если это другой клиент)
		if to_acc.client_id != user_id:
			to_contact = await uow.transactions.get_owner_contact(to_acc.client_id)
			if to_contact:
				uow.add_event(NotificationEvent(
					type="transaction_incoming",
					to=to_contact.email,
					variables={
						"account_number": to_acc.account_number, 
						"from_account": from_acc.account_number,
						"amount": f"{credited_amount} {to_acc.currency}", 
						"balance_after": str(to_acc.balance)
					}
				))

		# Бизнес-лог
		uow.add_event(LogEvent(
			user_id=user_id,
			action="transfer",
			service="transaction_service",
			details=f"Перевод {from_acc.account_number} -> {to_acc.account_number}",
			entity_id=tx_out.id,
			amount=float(amount),
			currency=from_acc.currency,
		))

		try:
			await uow.commit()
		except IntegrityError as exc:
			raise TransactionConflict("Ошибка записи транзакции. Попробуйте еще раз.") from exc

		await uow.transactions.refresh(tx_out)

		return tx_out


