"""Pydantic-схемы для банковских счетов."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Типы ───────────────────────────────────────────────────────────────

AccountType = Literal["checking", "savings", "credit", "deposit"]
Currency = Literal["RUB", "USD", "EUR"]
AccountStatus = Literal["open", "closed", "frozen"]


# ── Запросы ────────────────────────────────────────────────────────────

class OpenAccountRequest(BaseModel):
	"""Запрос на открытие банковского счёта."""

	type: AccountType = Field(description="Тип счёта: checking (расчётный), savings (накопительный), credit, deposit (вклад)")
	currency: Currency = Field(description="Валюта счёта: RUB, USD, EUR")

	model_config = ConfigDict(extra="forbid")


# ── Ответы ─────────────────────────────────────────────────────────────

class AccountResponse(BaseModel):
	"""Полные данные банковского счёта."""

	id: UUID = Field(description="UUID счёта")
	client_id: UUID = Field(description="UUID владельца")
	account_number: str = Field(description="20-значный номер счёта")
	type: AccountType = Field(description="Тип счёта")
	currency: Currency = Field(description="Валюта")
	balance: Decimal = Field(description="Текущий баланс")
	status: AccountStatus = Field(description="Статус счёта")
	opened_at: datetime = Field(description="Дата/время открытия")
	closed_at: datetime | None = Field(default=None, description="Дата/время закрытия")

	model_config = ConfigDict(from_attributes=True)


class AccountListResponse(BaseModel):
	"""Список счетов пользователя."""

	accounts: list[AccountResponse] = Field(description="Массив счетов")
	total: int = Field(description="Общее количество")


class AccountMessageResponse(BaseModel):
	"""Текстовый ответ операции со счётом."""

	message: str = Field(description="Сообщение о результате")
	account: AccountResponse = Field(description="Данные счёта")


__all__ = [
	"AccountListResponse",
	"AccountMessageResponse",
	"AccountResponse",
	"AccountStatus",
	"AccountType",
	"Currency",
	"OpenAccountRequest",
]
