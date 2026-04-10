"""Бизнес-логика обмена валют между счетами пользователя."""

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from shared import models
from shared.events.base import LogEvent, NotificationEvent

from .. import exchange_client
from ..exceptions import (
	AccountNotOpen,
	InsufficientFunds,
	RateUnavailable,
	SameAccountExchange,
	SameCurrencyExchange,
)
from ..uow import CurrencyUnitOfWork


async def exchange(
	uow: CurrencyUnitOfWork,
	user_id: UUID,
	from_account_id: UUID,
	to_account_id: UUID,
	amount: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
	"""Выполняет конвертацию средств между двумя счетами одного пользователя.

	Атомарная операция (Unit of Work):
	1. Блокировка обоих счетов (FOR UPDATE).
	2. Проверка доступности валют и суммы.
	3. Конвертация по актуальному курсу внешнего API.
	4. Создание проводок (транзакций) списания и зачисления.
	5. Регистрация событий NotificationEvent и LogEvent.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		user_id: ID владельца счетов.
		from_account_id: Счёт списания.
		to_account_id: Счёт зачисления.
		amount: Сумма списания в валюте 'from'.

	Returns:
		tuple[Decimal, Decimal, Decimal]: (списано, зачислено, курс).

	Raises:
		SameAccountExchange: Если счета совпадают.
		AccountNotFound: Если счета не найдены или не принадлежат пользователю.
		AccountNotOpen: Если счета закрыты или заморожены.
		SameCurrencyExchange: Если валюты счетов совпадают.
		InsufficientFunds: Если не хватает средств на счёте списания.
		RateUnavailable: Если не удалось получить актуальный курс или сохранить транзакцию.
	"""
	if from_account_id == to_account_id:
		raise SameAccountExchange("Обмен на тот же счёт невозможен.")

	async with uow:
		# 1. Атомарная блокировка счетов
		accounts = await uow.accounts.lock_accounts([from_account_id, to_account_id])
		from_acc = accounts.get(from_account_id)
		to_acc = accounts.get(to_account_id)

		if not from_acc or from_acc.client_id != user_id:
			from ..exceptions import AccountNotFound

			raise AccountNotFound(f"Счёт списания {from_account_id} не найден.")
		if not to_acc or to_acc.client_id != user_id:
			from ..exceptions import AccountNotFound

			raise AccountNotFound(f"Счёт зачисления {to_account_id} не найден.")

		# 2. Проверка статусов и валют
		if from_acc.status != "open":
			raise AccountNotOpen(f"Счёт списания в статусе «{from_acc.status}».")
		if to_acc.status != "open":
			raise AccountNotOpen(f"Счёт зачисления в статусе «{to_acc.status}».")

		if from_acc.currency == to_acc.currency:
			raise SameCurrencyExchange("Валюты совпадают — используйте обычный перевод.")

		if from_acc.balance < amount:
			raise InsufficientFunds(f"Недостаточно средств. Доступно: {from_acc.balance} {from_acc.currency}.")

		# 3. Получение курса
		try:
			rate, _ = await exchange_client.get_fresh_rate(from_acc.currency, to_acc.currency)
		except Exception as exc:
			raise RateUnavailable(f"Не удалось получить курс {from_acc.currency}/{to_acc.currency}: {exc}") from exc

		# 4. Расчёт суммы зачисления
		converted = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

		# 5. Проводки
		now = datetime.now(UTC)
		from_bal_before, to_bal_before = from_acc.balance, to_acc.balance

		from_acc.balance -= amount
		to_acc.balance += converted

		tx_desc = f"Обмен {from_acc.currency}→{to_acc.currency}, курс {rate}"

		tx_out = models.Transaction(
			id=uuid4(),
			account_id=from_account_id,
			type="exchange",
			amount=amount,
			created_at=now,
			description=tx_desc,
			related_account_id=to_account_id,
			direction="outgoing",
			status="posted",
			balance_before=from_bal_before,
			balance_after=from_acc.balance,
			external_ref=str(rate),
		)

		tx_in = models.Transaction(
			id=uuid4(),
			account_id=to_account_id,
			type="exchange",
			amount=converted,
			created_at=now,
			description=tx_desc,
			related_account_id=from_account_id,
			direction="incoming",
			status="posted",
			balance_before=to_bal_before,
			balance_after=to_acc.balance,
			external_ref=str(rate),
		)

		await uow.accounts.add_all([tx_out, tx_in])

		# 6. Регистрация событий в UoW
		contact = await uow.accounts.get_owner_contact(user_id)
		if contact:
			uow.add_event(
				NotificationEvent(
					type="transaction_transfer",
					to=contact.email,
					variables={
						"from_account": from_acc.account_number,
						"to_account": to_acc.account_number,
						"amount": f"{amount} {from_acc.currency} → {converted} {to_acc.currency}",
						"currency": from_acc.currency,
						"balance_after": str(from_acc.balance),
					},
				)
			)

		uow.add_event(
			LogEvent(
				user_id=user_id,
				action="currency_exchange",
				service="currency_service",
				details=f"Обмен {from_acc.currency} -> {to_acc.currency}",
				entity_id=tx_out.id,
				amount=float(amount),
				currency=from_acc.currency,
			)
		)

		try:
			await uow.commit()  # Выполняет коммит и публикует события
		except IntegrityError as exc:
			raise RateUnavailable("Системная ошибка при сохранении транзакции.") from exc

		return amount, converted, rate
