"""Бизнес-логика закрытия банковского счёта."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.rabbitmq.client import publish
from shared.rabbitmq.constants import (
	EMAIL_ROUTING_KEY,
	LOG_ACCOUNT_KEY,
	NOTIFICATIONS_EXCHANGE,
)
from shared.utils.log_event import log_event

from ..repository import AccountRepository
from ..exceptions import (
	AccountConflict,
	AccountNonZeroBalance,
	AccountNotOpen,
)


async def close_account(
	session: AsyncSession,
	user_id: UUID,
	account_id: UUID,
) -> models.BankAccount:
	"""Закрывает банковский счёт пользователя.

	Счёт может быть закрыт только если:
	1. Он принадлежит текущему пользователю.
	2. Его текущий статус - 'open'.
	3. Его баланс равен нулю.

	Args:
		session: Сессия БД.
		user_id: ID владельца.
		account_id: ID закрываемого счёта.

	Returns:
		BankAccount: Счёт в статусе 'closed'.

	Raises:
		AccountNotFound: Если счёт не найден.
		AccountNotOpen: Если счёт уже закрыт или заморожен.
		AccountNonZeroBalance: Если на счёте остались средства.
		AccountConflict: При системных ошибках обновления.
	"""
	repo = AccountRepository(session)
	
	# 1. Поиск и принадлежность
	account = await repo.get_by_user(user_id, account_id)

	# 2. Валидация состояния
	if account.status != "open":
		raise AccountNotOpen(
			f"Невозможно закрыть счёт со статусом «{account.status}»."
		)

	if account.balance != 0:
		raise AccountNonZeroBalance(
			f"На счёте остаток {account.balance} {account.currency}. "
			"Снимите все средства перед закрытием."
		)

	# 3. Закрытие
	account.status = "closed"
	account.closed_at = datetime.now(UTC)

	try:
		await repo.commit()
	except IntegrityError as exc:
		await repo.rollback()
		raise AccountConflict("Конфликт данных при закрытии счёта.") from exc

	await repo.refresh(account)

	# 4. Уведомление и логирование (Best effort)
	contact = await repo.get_owner_contact(user_id)
	if contact:
		try:
			await publish(
				exchange_name=NOTIFICATIONS_EXCHANGE,
				routing_key=EMAIL_ROUTING_KEY,
				body={
					"type": "account_closed",
					"payload": {
						"to": contact.email,
						"variables": {
							"account_number": account.account_number,
						},
					},
				},
			)
		except Exception:
			pass

	await log_event(
		routing_key=LOG_ACCOUNT_KEY,
		event_type="account",
		payload={
			"user_id": str(user_id),
			"action": "close_account",
			"service": "account_service",
			"entity_id": str(account.id),
			"entity_type": "bank_account",
			"status": "success",
			"details": f"Счёт {account.account_number} закрыт",
		}
	)

	return account
