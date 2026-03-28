"""Pydantic-схемы для транзакций."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Типы ───────────────────────────────────────────────────────────────

TransactionType = Literal["deposit", "withdrawal", "transfer", "exchange"]
TransactionDirection = Literal["incoming", "outgoing"]
TransactionStatus = Literal["pending", "posted", "failed"]


# ── Запросы ────────────────────────────────────────────────────────────

class DepositRequest(BaseModel):
	"""Запрос на пополнение счёта."""

	amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2, description="Сумма пополнения")
	description: str | None = Field(default=None, max_length=256, description="Комментарий")

	model_config = ConfigDict(extra="forbid")


class WithdrawalRequest(BaseModel):
	"""Запрос на снятие со счёта."""

	amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2, description="Сумма снятия")
	description: str | None = Field(default=None, max_length=256, description="Комментарий")

	model_config = ConfigDict(extra="forbid")


class TransferRequest(BaseModel):
	"""Запрос на перевод между счетами (свои или чужие внутри банка)."""

	to_account_id: UUID = Field(description="UUID счёта-получателя")
	amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2, description="Сумма перевода")
	description: str | None = Field(default=None, max_length=256, description="Комментарий")

	model_config = ConfigDict(extra="forbid")


# ── Ответы ─────────────────────────────────────────────────────────────

class TransactionResponse(BaseModel):
	"""Полные данные одной транзакции."""

	id: UUID = Field(description="UUID транзакции")
	account_id: UUID = Field(description="UUID счёта")
	type: TransactionType = Field(description="Тип операции")
	amount: Decimal = Field(description="Сумма")
	created_at: datetime = Field(description="Дата/время создания")
	description: str | None = Field(default=None, description="Комментарий")
	related_account_id: UUID | None = Field(default=None, description="Счёт-контрагент")
	direction: TransactionDirection = Field(description="Направление")
	status: TransactionStatus = Field(description="Статус")
	balance_before: Decimal = Field(description="Баланс до операции")
	balance_after: Decimal = Field(description="Баланс после операции")
	external_ref: str | None = Field(default=None, description="Внешняя ссылка")

	model_config = ConfigDict(from_attributes=True)


class TransactionMessageResponse(BaseModel):
	"""Ответ на выполнение операции."""

	message: str = Field(description="Сообщение о результате")
	transaction: TransactionResponse = Field(description="Данные транзакции")


class TransactionListResponse(BaseModel):
	"""Список транзакций с пагинацией."""

	transactions: list[TransactionResponse] = Field(description="Массив транзакций")
	total: int = Field(description="Общее количество (с учётом фильтров)")
	limit: int = Field(description="Лимит на страницу")
	offset: int = Field(description="Смещение")


__all__ = [
	"DepositRequest",
	"TransactionDirection",
	"TransactionListResponse",
	"TransactionMessageResponse",
	"TransactionResponse",
	"TransactionStatus",
	"TransactionType",
	"TransferRequest",
	"WithdrawalRequest",
]
