"""Бизнес-логика открытия и получения информации о банковских счетах."""

import secrets
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models, schemas
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
	AccountError,
	AccountLimitReached,
)

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


async def _generate_unique_number(repo: AccountRepository, account_type: str, currency: str) -> str:
	"""Генерирует уникальный 20-значный номер банковского счёта.

	Args:
		repo: Репозиторий счетов.
		account_type: Тип счёта.
		currency: Валюта.

	Returns:
		str: Генерируемый уникальный номер.

	Raises:
		AccountError: Если не удалось создать уникальный номер за 10 попыток.
	"""
	type_code = _ACCOUNT_TYPE_CODES[account_type]
	currency_code = _CURRENCY_CODES[currency]
	
	for _ in range(10):
		check_digit = str(secrets.randbelow(10))
		individual = str(secrets.randbelow(10_000_000)).zfill(7)
		number = f"{type_code}{currency_code}{check_digit}{_BRANCH_CODE}{individual}"
		
		if await repo.is_number_unique(number):
			return number
			
	raise AccountError("Системная ошибка: не удалось сгенерировать уникальный номер счёта.")


async def open_account(
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.OpenAccountRequest,
) -> models.BankAccount:
	"""Создаёт новый банковский счёт для активного пользователя.

	Проверяет лимиты на количество счетов одного типа и валюты.
	При успехе генерирует номер счёта, отправляет уведомление и регистрирует событие в лог.

	Args:
		session: Сессия БД.
		user_id: ID владельца.
		payload: Параметры счёта (тип, валюта).

	Returns:
		BankAccount: Созданная ORM-модель счёта.

	Raises:
		AccountOwnerNotFound: Если пользователь не найден или заблокирован.
		AccountLimitReached: Если превышен лимит открытых счетов.
		AccountConflict: При коллизии данных в БД.
	"""
	repo = AccountRepository(session)
	
	# 1. Проверка владельца
	await repo.get_active_owner(user_id)

	# 2. Проверка лимитов
	count = await repo.count_open_by_type(user_id, payload.type, payload.currency)
	if count >= MAX_ACCOUNTS_PER_TYPE_CURRENCY:
		raise AccountLimitReached(
			f"Максимум {MAX_ACCOUNTS_PER_TYPE_CURRENCY} открытых счетов "
			f"типа «{payload.type}» в валюте {payload.currency}."
		)

	# 3. Генерация номера
	account_number = await _generate_unique_number(repo, payload.type, payload.currency)

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
	await repo.add(account)

	try:
		await repo.commit()
	except IntegrityError as exc:
		await repo.rollback()
		raise AccountConflict("Конфликт при создании счёта. Попробуйте еще раз.") from exc

	await repo.refresh(account)

	# 5. Уведомление и логирование (Best effort)
	contact = await repo.get_owner_contact(user_id)
	if contact:
		try:
			await publish(
				exchange_name=NOTIFICATIONS_EXCHANGE,
				routing_key=EMAIL_ROUTING_KEY,
				body={
					"type": "account_opened",
					"payload": {
						"to": contact.email,
						"variables": {
							"account_type": _TYPE_LABELS.get(account.type, account.type),
							"currency": account.currency,
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
			"action": "open_account",
			"service": "account_service",
			"entity_id": str(account.id),
			"entity_type": "bank_account",
			"status": "success",
			"details": f"Открыт счёт {account.account_number} ({payload.type})",
		}
	)

	return account


async def list_accounts(session: AsyncSession, user_id: UUID) -> Sequence[models.BankAccount]:
	"""Возвращает список всех счетов пользователя.

	Args:
		session: Сессия БД.
		user_id: ID пользователя.

	Returns:
		Sequence[BankAccount]: Список счетов (включая закрытые/замороженные).
	"""
	repo = AccountRepository(session)
	return await repo.list_by_user(user_id)


async def get_account(session: AsyncSession, user_id: UUID, account_id: UUID) -> models.BankAccount:
	"""Возвращает детальную информацию о конкретном счёте.

	Args:
		session: Сессия БД.
		user_id: ID пользователя.
		account_id: ID счёта.

	Returns:
		BankAccount: Объект счёта.

	Raises:
		AccountNotFound: Если счёт не найден или принадлежит не этому пользователю.
	"""
	repo = AccountRepository(session)
	return await repo.get_by_user(user_id, account_id)
