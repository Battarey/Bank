"""Бизнес-логика заморозки и разморозки банковских счетов."""

from datetime import UTC, datetime
from uuid import UUID

from shared import models
from shared.events.base import LogEvent, NotificationEvent

from ..uow import AccountUnitOfWork
from ..exceptions import (
	AccountAlreadyFrozen,
	AccountNotFrozen,
	AccountNotOpen,
	UnfreezeNotAllowed,
)


async def freeze_account(
	uow: AccountUnitOfWork,
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
		uow: Unit of Work для управления транзакцией и событиями.
		user_id: ID владельца.
		account_id: ID счёта.
		frozen_by: Кем заморожен ('user', 'system', 'admin').
		reason: Причина заморозки.

	Returns:
		models.BankAccount: Замороженный счёт в статусе 'frozen'.

	Raises:
		AccountNotFound: Если счёт не найден.
		AccountAlreadyFrozen: Если счёт уже в статусе frozen.
		AccountNotOpen: Если счёт уже закрыт.
	"""
	async with uow:
		account = await uow.accounts.get_by_user(user_id, account_id)

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

		# Регистрация событий ДО коммита для авто-публикации
		contact = await uow.accounts.get_owner_contact(user_id)
		if contact:
			uow.add_event(NotificationEvent(
				type="account_frozen",
				to=contact.email,
				variables={
					"account_number": account.account_number,
					"frozen_by": frozen_by,
					"reason": reason,
				},
			))

		uow.add_event(LogEvent(
			user_id=user_id,
			action="freeze_account",
			service="account_service",
			details=f"Счёт {account.account_number} заморожен ({frozen_by}: {reason})",
			entity_id=account.id,
			entity_type="bank_account",
		))

		await uow.commit()
		await uow.accounts.refresh(account)

	return account


async def unfreeze_account(
	uow: AccountUnitOfWork,
	user_id: UUID,
	account_id: UUID,
) -> models.BankAccount:
	"""Размораживает счёт, если он был заморожен пользователем.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		user_id: ID владельца.
		account_id: ID счёта.

	Returns:
		models.BankAccount: Размороженный счёт в статусе 'open'.

	Raises:
		AccountNotFound: Если счёт не найден.
		AccountNotFrozen: Если счёт не находится в статусе заморозки.
		UnfreezeNotAllowed: Если счёт заморожен системой безопасности (не пользователем).
	"""
	async with uow:
		account = await uow.accounts.get_by_user(user_id, account_id)

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

		# Регистрация событий
		contact = await uow.accounts.get_owner_contact(user_id)
		if contact:
			uow.add_event(NotificationEvent(
				type="account_unfrozen",
				to=contact.email,
				variables={
					"account_number": account.account_number,
				},
			))

		uow.add_event(LogEvent(
			user_id=user_id,
			action="unfreeze_account",
			service="account_service",
			details=f"Счёт {account.account_number} разморожен",
			entity_id=account.id,
			entity_type="bank_account",
		))

		await uow.commit()
		await uow.accounts.refresh(account)

	return account


async def cascade_freeze(
	uow: AccountUnitOfWork,
	user_id: UUID,
	*,
	reason: str = "Блокировка аккаунта",
) -> int:
	"""Системная каскадная заморозка всех открытых счетов пользователя.

	Используется при блокировке аккаунта или подозрении на фрод.

	Args:
		uow: Unit of Work для управления транзакциями.
		user_id: ID владельца счетов.
		reason: Причина массовой заморозки.

	Returns:
		int: Количество замороженных счетов.
	"""
	async with uow:
		accounts = await uow.accounts.get_open_accounts(user_id)

		now = datetime.now(UTC)
		count = 0
		for acc in accounts:
			acc.status = "frozen"
			acc.frozen_by = "system"
			acc.frozen_at = now
			acc.freeze_reason = reason
			count += 1
			
			uow.add_event(LogEvent(
				user_id=user_id,
				action="cascade_freeze_account",
				service="account_service",
				details=f"Счёт {acc.account_number} заморожен системой: {reason}",
				entity_id=acc.id,
				entity_type="bank_account",
			))

		if count:
			await uow.commit()

	return count


async def cascade_unfreeze(
	uow: AccountUnitOfWork,
	user_id: UUID,
) -> int:
	"""Каскадная разморозка счетов, замороженных системой.

	Args:
		uow: Unit of Work для управления транзакциями.
		user_id: ID владельца счетов.

	Returns:
		int: Количество размороженных счетов.
	"""
	async with uow:
		accounts = await uow.accounts.get_system_frozen_accounts(user_id)

		count = 0
		for acc in accounts:
			acc.status = "open"
			acc.frozen_by = None
			acc.frozen_at = None
			acc.freeze_reason = None
			count += 1
			
			uow.add_event(LogEvent(
				user_id=user_id,
				action="cascade_unfreeze_account",
				service="account_service",
				details=f"Счёт {acc.account_number} разморожен системой",
				entity_id=acc.id,
				entity_type="bank_account",
			))

		if count:
			await uow.commit()

	return count
