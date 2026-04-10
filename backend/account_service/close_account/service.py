"""Бизнес-логика закрытия банковского счёта."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from shared import models
from shared.events.base import LogEvent, NotificationEvent

from ..exceptions import (
	AccountConflict,
	AccountNonZeroBalance,
	AccountNotOpen,
)
from ..uow import AccountUnitOfWork


async def close_account(
	uow: AccountUnitOfWork,
	user_id: UUID,
	account_id: UUID,
) -> models.BankAccount:
	"""Закрывает банковский счёт пользователя.

	Счёт может быть закрыт только если:
	1. Он принадлежит текущему пользователю.
	2. Его текущий статус - 'open'.
	3. Его баланс равен нулю.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		user_id: ID владельца.
		account_id: ID закрываемого счёта.

	Returns:
		models.BankAccount: Счёт в статусе 'closed'.

	Raises:
		AccountNotFound: Если счёт не найден.
		AccountNotOpen: Если счёт уже закрыт или заморожен.
		AccountNonZeroBalance: Если на счёте остались средства.
		AccountConflict: При системных ошибках обновления.
	"""
	async with uow:
		# 1. Поиск и принадлежность
		account = await uow.accounts.get_by_user(user_id, account_id)

		# 2. Валидация состояния
		if account.status != "open":
			raise AccountNotOpen(f"Невозможно закрыть счёт со статусом «{account.status}».")

		if account.balance != 0:
			raise AccountNonZeroBalance(
				f"На счёте остаток {account.balance} {account.currency}. Снимите все средства перед закрытием."
			)

		# 3. Закрытие
		account.status = "closed"
		account.closed_at = datetime.now(UTC)

		# 4. Регистрация событий ДО коммита
		contact = await uow.accounts.get_owner_contact(user_id)
		if contact:
			uow.add_event(
				NotificationEvent(
					type="account_closed",
					to=contact.email,
					variables={
						"account_number": account.account_number,
					},
				)
			)

		uow.add_event(
			LogEvent(
				user_id=user_id,
				action="close_account",
				service="account_service",
				details=f"Счёт {account.account_number} закрыт",
				entity_id=account.id,
				entity_type="bank_account",
			)
		)

		try:
			await uow.commit()
		except IntegrityError as exc:
			raise AccountConflict("Конфликт данных при закрытии счёта.") from exc

		await uow.accounts.refresh(account)

	return account
