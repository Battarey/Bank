"""Бизнес-логика открытия банковского счёта."""

import logging
import secrets
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models, schemas
from shared.rabbitmq.client import publish
from shared.rabbitmq.constants import NOTIFICATIONS_EXCHANGE, EMAIL_ROUTING_KEY
from account_service.exceptions import (
	AccountConflict,
	AccountError,
	AccountLimitReached,
	AccountOwnerNotFound,
)

logger = logging.getLogger("account_service")


# ── Константы ──────────────────────────────────────────────────────────

MAX_ACCOUNTS_PER_TYPE_CURRENCY = 3

# Коды балансовых счетов (первые 5 цифр номера)
_ACCOUNT_TYPE_CODES: dict[str, str] = {
	"checking": "40817",
	"savings": "42301",
	"credit": "45505",
	"deposit": "42305",
}

# Коды валют (позиции 6–8 номера)
_CURRENCY_CODES: dict[str, str] = {
	"RUB": "810",
	"USD": "840",
	"EUR": "978",
}

_BRANCH_CODE = "0001"

# Названия типов счетов для уведомлений
_TYPE_LABELS: dict[str, str] = {
	"checking": "Расчётный",
	"savings": "Накопительный",
	"credit": "Кредитный",
	"deposit": "Вклад",
}


# ── Генерация номера счёта ─────────────────────────────────────────────

def _generate_account_number(account_type: str, currency: str) -> str:
	"""Генерирует 20-значный номер банковского счёта.

	Формат: TTTTTCCCК BBBBNNNNNNN
	  T (5) — код балансового счёта
	  C (3) — код валюты
	  К (1) — контрольная цифра
	  B (4) — код отделения
	  N (7) — индивидуальный номер
	"""
	type_code = _ACCOUNT_TYPE_CODES[account_type]
	currency_code = _CURRENCY_CODES[currency]
	check_digit = str(secrets.randbelow(10))
	individual = str(secrets.randbelow(10_000_000)).zfill(7)
	return f"{type_code}{currency_code}{check_digit}{_BRANCH_CODE}{individual}"


async def _is_number_unique(session: AsyncSession, number: str) -> bool:
	"""Проверяет уникальность номера счёта в БД."""
	stmt = select(models.BankAccount.id).where(models.BankAccount.account_number == number)
	result = await session.execute(stmt)
	return result.first() is None


async def _generate_unique_number(session: AsyncSession, account_type: str, currency: str) -> str:
	"""Генерирует уникальный 20-значный номер (до 10 попыток)."""
	for _ in range(10):
		number = _generate_account_number(account_type, currency)
		if await _is_number_unique(session, number):
			return number
	raise AccountError("Не удалось сгенерировать уникальный номер счёта.")


# ── Уведомления ────────────────────────────────────────────────────────

async def _notify_account_opened(
	session: AsyncSession,
	user_id: UUID,
	account: models.BankAccount,
) -> None:
	"""Отправляет email-уведомление об открытии счёта."""
	contact = await session.get(models.Contact, user_id)
	if not contact:
		return
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


# ── Операции ───────────────────────────────────────────────────────────

async def open_account(
	session: AsyncSession,
	user_id: UUID,
	payload: schemas.OpenAccountRequest,
) -> models.BankAccount:
	"""Открывает новый банковский счёт для пользователя."""

	# 1. Проверяем, что пользователь существует и активен
	user = await session.get(models.User, user_id)
	if user is None or user.status != "active":
		raise AccountOwnerNotFound("Пользователь не найден или не активен.")

	# 2. Проверяем лимит: не более N счетов одного типа + валюты
	stmt = (
		select(models.BankAccount)
		.where(
			models.BankAccount.client_id == user_id,
			models.BankAccount.type == payload.type,
			models.BankAccount.currency == payload.currency,
			models.BankAccount.status == "open",
		)
	)
	result = await session.execute(stmt)
	existing = result.scalars().all()
	if len(existing) >= MAX_ACCOUNTS_PER_TYPE_CURRENCY:
		raise AccountLimitReached(
			f"Максимум {MAX_ACCOUNTS_PER_TYPE_CURRENCY} открытых счетов "
			f"типа «{payload.type}» в валюте {payload.currency}."
		)

	# 3. Генерируем уникальный номер
	account_number = await _generate_unique_number(session, payload.type, payload.currency)

	# 4. Создаём счёт
	now = datetime.now(UTC)
	account = models.BankAccount(
		id=uuid4(),
		client_id=user_id,
		account_number=account_number,
		type=payload.type,
		currency=payload.currency,
		balance=Decimal("0.00"),
		status="open",
		opened_at=now,
	)
	session.add(account)

	try:
		await session.commit()
		await session.refresh(account)
	except IntegrityError:
		await session.rollback()
		raise AccountConflict("Конфликт данных при создании счёта. Попробуйте снова.")

	logger.info(
		"Счёт открыт: user=%s, account=%s, type=%s, currency=%s",
		user_id, account.id, payload.type, payload.currency,
	)

	await _notify_account_opened(session, user_id, account)

	return account


async def list_accounts(
	session: AsyncSession,
	user_id: UUID,
) -> list[models.BankAccount]:
	"""Возвращает все счета пользователя."""

	stmt = (
		select(models.BankAccount)
		.where(models.BankAccount.client_id == user_id)
		.order_by(models.BankAccount.opened_at.desc())
	)
	result = await session.execute(stmt)
	return list(result.scalars().all())


async def get_account(
	session: AsyncSession,
	user_id: UUID,
	account_id: UUID,
) -> models.BankAccount:
	"""Возвращает счёт по ID, если он принадлежит пользователю."""

	account = await session.get(models.BankAccount, account_id)
	if account is None or account.client_id != user_id:
		from account_service.exceptions import AccountNotFound
		raise AccountNotFound("Счёт не найден.")
	return account


__all__ = [
	"get_account",
	"list_accounts",
	"open_account",
]
