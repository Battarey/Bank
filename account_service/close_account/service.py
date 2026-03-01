"""Бизнес-логика закрытия банковского счёта."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shared import models


# ── Исключения ─────────────────────────────────────────────────────────

class CloseAccountError(Exception):
	"""Базовая ошибка закрытия счёта."""


class CloseAccountNotFound(CloseAccountError):
	"""Счёт не найден или не принадлежит пользователю."""


class CloseAccountNotOpen(CloseAccountError):
	"""Счёт уже закрыт или заморожен."""


class CloseAccountNonZeroBalance(CloseAccountError):
	"""На счёте есть остаток — невозможно закрыть."""


# ── Операции ───────────────────────────────────────────────────────────

async def close_account(
	session: AsyncSession,
	user_id: UUID,
	account_id: UUID,
) -> models.BankAccount:
	"""Закрывает банковский счёт (status → closed, closed_at → now).

	Предусловия:
	  - Счёт принадлежит пользователю.
	  - Статус = open.
	  - Баланс = 0.
	"""

	account = await session.get(models.BankAccount, account_id)

	# 1. Существование и принадлежность
	if account is None or account.client_id != user_id:
		raise CloseAccountNotFound("Счёт не найден.")

	# 2. Статус
	if account.status != "open":
		raise CloseAccountNotOpen(
			f"Невозможно закрыть счёт со статусом «{account.status}»."
		)

	# 3. Баланс
	if account.balance != Decimal("0.00"):
		raise CloseAccountNonZeroBalance(
			f"На счёте остаток {account.balance} {account.currency}. "
			"Переведите средства перед закрытием."
		)

	# 4. Закрываем
	account.status = "closed"
	account.closed_at = datetime.now(UTC)

	try:
		await session.commit()
		await session.refresh(account)
	except Exception:
		await session.rollback()
		raise

	return account


__all__ = [
	"CloseAccountError",
	"CloseAccountNonZeroBalance",
	"CloseAccountNotFound",
	"CloseAccountNotOpen",
	"close_account",
]
