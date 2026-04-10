"""Бизнес-логика открытия и получения информации о банковских счетах."""

import secrets
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from shared import models, schemas
from shared.events.base import LogEvent, NotificationEvent

from ..exceptions import (
	AccountConflict,
	AccountError,
	AccountLimitReached,
)
from ..uow import AccountUnitOfWork

# ── Константы ──────────────────────────────────────────────────────────

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


async def _generate_unique_number(uow: AccountUnitOfWork, account_type: str, currency: str) -> str:
	"""Генерирует уникальный 20-значный номер банковского счёта.

	Формат: [Тип][Валюта][Бранч][Рандом] (5 + 3 + 4 + 8 = 20 цифр).

	Args:
		uow: Unit of Work для проверки уникальности.
		account_type: Тип счёта (checking, savings и т.д.).
		currency: Валюта (RUB, USD, EUR).

	Returns:
		str: Уникальный 20-значный номер счёта.

	Raises:
		AccountError: Если после 10 попыток не удалось сгенерировать уникальный номер.
	"""
	type_prefix = _ACCOUNT_TYPE_CODES.get(account_type, "40817")
	curr_prefix = _CURRENCY_CODES.get(currency, "810")
	branch = _BRANCH_CODE

	for _ in range(10):
		random_part = "".join(str(secrets.randbelow(10)) for _ in range(8))
		number = f"{type_prefix}{curr_prefix}{branch}{random_part}"

		# Проверка уникальности
		existing = await uow.accounts.get_by_number(number)
		if not existing:
			return number

	raise AccountError("Системная ошибка: не удалось сгенерировать уникальный номер счёта после 10 попыток.")


async def open_account(
	uow: AccountUnitOfWork,
	user_id: UUID,
	payload: schemas.OpenAccountRequest,
) -> models.BankAccount:
	"""Создаёт новый банковский счёт для активного пользователя.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		user_id: ID владельца счёта.
		payload: Схема с параметрами открытия счёта (тип, валюта).

	Returns:
		models.BankAccount: Созданный счёт в статусе 'open'.

	Raises:
		AccountNotFound: Если пользователь не найден.
		AccountLimitReached: Если превышен лимит открытых счетов данного типа.
		AccountConflict: При коллизии номера счёта или других проблемах целостности.
	"""
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

		# 5. Регистрация событий ДО коммита
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
	"""Возвращает список всех счетов пользователя через Query Layer (CQRS).

	Args:
		uow: Unit of Work для доступа к репозиторию.
		user_id: ID владельца счетов.

	Returns:
		tuple[list[schemas.AccountResponse], int]: Список объектов счетов и их общее количество.
	"""
	async with uow:
		return await uow.account_queries.list_by_user_with_total(user_id)


async def get_account(uow: AccountUnitOfWork, user_id: UUID, account_id: UUID) -> schemas.AccountResponse:
	"""Возвращает детальную информацию о конкретном счёте через Query Layer (CQRS).

	Args:
		uow: Unit of Work для доступа к репозиторию.
		user_id: ID владельца счёта.
		account_id: ID запрашиваемого счёта.

	Returns:
		schemas.AccountResponse: Объект счёта.

	Raises:
		AccountNotFound: Если счёт не найден или не принадлежит пользователю.
	"""
	async with uow:
		account = await uow.account_queries.get_by_id_raw(user_id, account_id)
		if not account:
			from ..exceptions import AccountNotFound

			raise AccountNotFound("Счёт не найден или не принадлежит вам.")
		return account
