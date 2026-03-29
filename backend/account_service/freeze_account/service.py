"""Бизнес-логика заморозки и разморозки банковских счетов."""

from datetime import UTC, datetime
from uuid import UUID

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
	AccountAlreadyFrozen,
	AccountNotFrozen,
	AccountNotOpen,
	UnfreezeNotAllowed,
)


async def freeze_account(
	session: AsyncSession,
	user_id: UUID,
	account_id: UUID,
	*,
	frozen_by: str = "user",
	reason: str = "Заморозка по запросу пользователя",
) -> models.BankAccount:
	"""Замораживает счёт, предотвращая любые расходные операции.

	1. Проверяет наличие счёта и принадлежность пользователю.
	2. Переводит в статус 'frozen', сохраняя метаданные заморозки.
	3. Отправляет уведомление и логирует событие.

	Args:
		session: Сессия БД.
		user_id: ID владельца.
		account_id: ID счёта.
		frozen_by: Кем заморожен ('user', 'system', 'admin').
		reason: Причина заморозки.

	Returns:
		BankAccount: Замороженный счёт.

	Raises:
		AccountNotFound: Если счёт не найден.
		AccountAlreadyFrozen: Если счёт уже в статусе frozen.
		AccountNotOpen: Если счёт закрыт.
	"""
	repo = AccountRepository(session)
	account = await repo.get_by_user(user_id, account_id)

	if account.status == "frozen":
		raise AccountAlreadyFrozen(f"Счёт {account.account_number} уже заморожен.")

	if account.status != "open":
		raise AccountNotOpen(
			f"Невозможно заморозить счёт в статусе «{account.status}»."
		)

	now = datetime.now(UTC)
	account.status = "frozen"
	account.frozen_by = frozen_by
	account.frozen_at = now
	account.freeze_reason = reason

	try:
		await repo.commit()
	except Exception:
		await repo.rollback()
		raise

	await repo.refresh(account)

	# Уведомление и логирование (Best effort)
	contact = await repo.get_owner_contact(user_id)
	if contact:
		try:
			await publish(
				exchange_name=NOTIFICATIONS_EXCHANGE,
				routing_key=EMAIL_ROUTING_KEY,
				body={
					"type": "account_frozen",
					"payload": {
						"to": contact.email,
						"variables": {
							"account_number": account.account_number,
							"frozen_by": frozen_by,
							"reason": reason,
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
			"action": "freeze_account",
			"service": "account_service",
			"entity_id": str(account.id),
			"entity_type": "bank_account",
			"status": "success",
			"details": f"Счёт {account.account_number} заморожен ({frozen_by}: {reason})",
		}
	)

	return account


async def unfreeze_account(
	session: AsyncSession,
	user_id: UUID,
	account_id: UUID,
) -> models.BankAccount:
	"""Размораживает счёт, если он был заморожен пользователем.

	Системные заморозки (например, при блокировке профиля) нельзя снять вручную.

	Args:
		session: Сессия БД.
		user_id: ID владельца.
		account_id: ID счёта.

	Returns:
		BankAccount: Размороженный счёт в статусе 'open'.

	Raises:
		AccountNotFrozen: Если счёт не заморожен.
		UnfreezeNotAllowed: Если заморозка была инициирована системой.
	"""
	repo = AccountRepository(session)
	account = await repo.get_by_user(user_id, account_id)

	if account.status != "frozen":
		raise AccountNotFrozen(f"Счёт {account.account_number} не заморожен.")

	if account.frozen_by != "user":
		raise UnfreezeNotAllowed(
			"Счёт заморожен системой безопасности. Самостоятельная разморозка невозможна."
		)

	account.status = "open"
	account.frozen_by = None
	account.frozen_at = None
	account.freeze_reason = None

	try:
		await repo.commit()
	except Exception:
		await repo.rollback()
		raise

	await repo.refresh(account)

	# Уведомление и логирование (Best effort)
	contact = await repo.get_owner_contact(user_id)
	if contact:
		try:
			await publish(
				exchange_name=NOTIFICATIONS_EXCHANGE,
				routing_key=EMAIL_ROUTING_KEY,
				body={
					"type": "account_unfrozen",
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
			"action": "unfreeze_account",
			"service": "account_service",
			"entity_id": str(account.id),
			"entity_type": "bank_account",
			"status": "success",
			"details": f"Счёт {account.account_number} разморожен",
		}
	)

	return account


async def cascade_freeze(
	session: AsyncSession,
	user_id: UUID,
	*,
	reason: str = "Блокировка аккаунта",
) -> int:
	"""Системная каскадная заморозка всех открытых счетов пользователя.

	Используется при блокировке профиля.

	Args:
		session: Сессия БД.
		user_id: ID пользователя.
		reason: Причина заморозки.

	Returns:
		int: Количество замороженных счетов.
	"""
	repo = AccountRepository(session)
	accounts = await repo.get_open_accounts(user_id) # Метод уже есть в репозитории

	now = datetime.now(UTC)
	count = 0
	for acc in accounts:
		acc.status = "frozen"
		acc.frozen_by = "system"
		acc.frozen_at = now
		acc.freeze_reason = reason
		count += 1

	if count:
		await repo.commit()

	return count


async def cascade_unfreeze(
	session: AsyncSession,
	user_id: UUID,
) -> int:
	"""Каскадная разморозка счетов, замороженных системой.

	Args:
		session: Сессия БД.
		user_id: ID пользователя.

	Returns:
		int: Количество размороженных счетов.
	"""
	repo = AccountRepository(session)
	accounts = await repo.get_system_frozen_accounts(user_id) # Метод уже есть в репозитории

	count = 0
	for acc in accounts:
		acc.status = "open"
		acc.frozen_by = None
		acc.frozen_at = None
		acc.freeze_reason = None
		count += 1

	if count:
		await repo.commit()

	return count
