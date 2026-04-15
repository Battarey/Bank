"""Бизнес-логика управления банковскими счетами."""

import secrets
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from shared import models, schemas
from shared.events.base import LogEvent, NotificationEvent

from ..core.exceptions import (
	AccountAlreadyFrozen,
	AccountConflict,
	AccountError,
	AccountLimitReached,
	AccountNotFound,
	AccountNotFrozen,
	AccountNotOpen,
	AccountNonZeroBalance,
	UnfreezeNotAllowed,
)
from ..core.uow import AccountUnitOfWork

# --- Константы ---

MAX_ACCOUNTS_PER_TYPE_CURRENCY = 3

_ACCOUNT_TYPE_CODES: dict[str, str] = {
	"checking": "40817",
	"savings": "42301",
	"credit": "45505",
	"deposit": "42305",
}

_CURRENCY_CODES: dict[str, str] = {
	"RUB": "810",
	"USD": "840",
	"EUR": "978",
}

_BRANCH_CODE = "0001"

_TYPE_LABELS: dict[str, str] = {
	"checking": "Расчётный",
	"savings": "Накопительный",
	"credit": "Кредитный",
	"deposit": "Вклад",
}


# --- Утилиты ---


async def _generate_unique_number(uow: AccountUnitOfWork, account_type: str, currency: str) -> str:
	"""Генерирует уникальный 20-значный номер банковского счёта."""
	type_prefix = _ACCOUNT_TYPE_CODES.get(account_type, "40817")
	curr_prefix = _CURRENCY_CODES.get(currency, "810")
	branch = _BRANCH_CODE

	for _ in range(10):
		random_part = "".join(str(secrets.randbelow(10)) for _ in range(8))
		number = f"{type_prefix}{curr_prefix}{branch}{random_part}"

		existing = await uow.accounts.get_by_number(number)
		if not existing:
			return number

	raise AccountError("Системная ошибка: не удалось сгенерировать уникальный номер счёта после 10 попыток.")


# --- Бизнес-логика ---


async def open_account(
	uow: AccountUnitOfWork,
	user_id: UUID,
	payload: schemas.OpenAccountRequest,
) -> models.BankAccount:
	"""Создаёт новый банковский счёт для активного пользователя."""
	async with uow:
		# 1. Проверка владельца
		await uow.accounts.get_active_owner(user_id)

		# 2. Проверка лимитов
		count = await uow.accounts.count_open_by_type(user_id, payload.type, payload.currency)
		if count >= MAX_ACCOUNTS_PER_TYPE_CURRENCY:
			raise AccountLimitReached(
				f"Максимум {MAX_ACCOUNTS_PER_TYPE_CURRENCY} открытых счетов "
				f"типа «{payload.type}» в валюте {payload.currency}."
			)

		# 3. Генерация номера
		account_number = await _generate_unique_number(uow, payload.type, payload.currency)

		# 4. Создание записи
		account = models.BankAccount(
			id=uuid4(),
			client_id=user_id,
			account_number=account_number,
			type=payload.type,
			currency=payload.currency,
			balance=Decimal("0.00"),
			status="open",
			opened_at=datetime.now(UTC),
		)
		await uow.accounts.add(account)

		# 5. Регистрация событий
		contact = await uow.accounts.get_owner_contact(user_id)
		if contact:
			uow.add_event(
				NotificationEvent(
					type="account_opened",
					to=contact.email,
					variables={
						"account_type": _TYPE_LABELS.get(account.type, account.type),
						"currency": account.currency,
						"account_number": account.account_number,
					},
				)
			)

		uow.add_event(
			LogEvent(
				user_id=user_id,
				action="open_account",
				service="account_service",
				details=f"Открыт счёт {account.account_number} ({payload.type})",
				entity_id=account.id,
				entity_type="bank_account",
			)
		)

		try:
			await uow.commit()
		except IntegrityError as exc:
			raise AccountConflict("Конфликт при создании счёта. Попробуйте еще раз.") from exc

		await uow.accounts.refresh(account)

	return account


async def list_accounts(uow: AccountUnitOfWork, user_id: UUID) -> tuple[list[schemas.AccountResponse], int]:
	"""Возвращает список всех счетов пользователя через Query Layer."""
	async with uow:
		return await uow.account_queries.list_by_user_with_total(user_id)


async def get_account(uow: AccountUnitOfWork, user_id: UUID, account_id: UUID) -> schemas.AccountResponse:
	"""Возвращает детальную информацию о конкретном счёте через Query Layer."""
	async with uow:
		account = await uow.account_queries.get_by_id_raw(user_id, account_id)
		if not account:
			raise AccountNotFound("Счёт не найден или не принадлежит вам.")
		return account


async def close_account(
	uow: AccountUnitOfWork,
	user_id: UUID,
	account_id: UUID,
) -> models.BankAccount:
	"""Закрывает банковский счёт пользователя."""
	async with uow:
		account = await uow.accounts.get_by_user(user_id, account_id)

		if account.status != "open":
			raise AccountNotOpen(f"Невозможно закрыть счёт со статусом «{account.status}».")

		if account.balance != 0:
			raise AccountNonZeroBalance(
				f"На счёте остаток {account.balance} {account.currency}. Снимите все средства перед закрытием."
			)

		account.status = "closed"
		account.closed_at = datetime.now(UTC)

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


async def freeze_account(
	uow: AccountUnitOfWork,
	user_id: UUID,
	account_id: UUID,
	*,
	frozen_by: str = "user",
	reason: str = "Заморозка по запросу пользователя",
) -> models.BankAccount:
	"""Замораживает счёт, предотвращая расходные операции."""
	async with uow:
		account = await uow.accounts.get_by_user(user_id, account_id)

		if account.status == "frozen":
			raise AccountAlreadyFrozen(f"Счёт {account.account_number} уже заморожен.")

		if account.status != "open":
			raise AccountNotOpen(f"Невозможно заморозить счёт в статусе «{account.status}».")

		now = datetime.now(UTC)
		account.status = "frozen"
		account.frozen_by = frozen_by
		account.frozen_at = now
		account.freeze_reason = reason

		contact = await uow.accounts.get_owner_contact(user_id)
		if contact:
			uow.add_event(
				NotificationEvent(
					type="account_frozen",
					to=contact.email,
					variables={
						"account_number": account.account_number,
						"frozen_by": frozen_by,
						"reason": reason,
					},
				)
			)

		uow.add_event(
			LogEvent(
				user_id=user_id,
				action="freeze_account",
				service="account_service",
				details=f"Счёт {account.account_number} заморожен ({frozen_by}: {reason})",
				entity_id=account.id,
				entity_type="bank_account",
			)
		)

		await uow.commit()
		await uow.accounts.refresh(account)

	return account


async def unfreeze_account(
	uow: AccountUnitOfWork,
	user_id: UUID,
	account_id: UUID,
) -> models.BankAccount:
	"""Размораживает счёт, если он был заморожен пользователем."""
	async with uow:
		account = await uow.accounts.get_by_user(user_id, account_id)

		if account.status != "frozen":
			raise AccountNotFrozen(f"Счёт {account.account_number} не заморожен.")

		if account.frozen_by != "user":
			raise UnfreezeNotAllowed("Счёт заморожен системой безопасности. Самостоятельная разморозка невозможна.")

		account.status = "open"
		account.frozen_by = None
		account.frozen_at = None
		account.freeze_reason = None

		contact = await uow.accounts.get_owner_contact(user_id)
		if contact:
			uow.add_event(
				NotificationEvent(
					type="account_unfrozen",
					to=contact.email,
					variables={
						"account_number": account.account_number,
					},
				)
			)

		uow.add_event(
			LogEvent(
				user_id=user_id,
				action="unfreeze_account",
				service="account_service",
				details=f"Счёт {account.account_number} разморожен",
				entity_id=account.id,
				entity_type="bank_account",
			)
		)

		await uow.commit()
		await uow.accounts.refresh(account)

	return account


async def cascade_freeze(
	uow: AccountUnitOfWork,
	user_id: UUID,
	*,
	reason: str = "Блокировка аккаунта",
) -> int:
	"""Системная каскадная заморозка всех открытых счетов пользователя."""
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

			uow.add_event(
				LogEvent(
					user_id=user_id,
					action="cascade_freeze_account",
					service="account_service",
					details=f"Счёт {acc.account_number} заморожен системой: {reason}",
					entity_id=acc.id,
					entity_type="bank_account",
				)
			)

		if count:
			await uow.commit()

	return count


async def cascade_unfreeze(
	uow: AccountUnitOfWork,
	user_id: UUID,
) -> int:
	"""Каскадная разморозка счетов, замороженных системой."""
	async with uow:
		accounts = await uow.accounts.get_system_frozen_accounts(user_id)

		count = 0
		for acc in accounts:
			acc.status = "open"
			acc.frozen_by = None
			acc.frozen_at = None
			acc.freeze_reason = None
			count += 1

			uow.add_event(
				LogEvent(
					user_id=user_id,
					action="cascade_unfreeze_account",
					service="account_service",
					details=f"Счёт {acc.account_number} разморожен системой",
					entity_id=acc.id,
					entity_type="bank_account",
				)
			)

		if count:
			await uow.commit()

	return count
