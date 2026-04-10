"""Pydantic-схемы для валютного сервиса."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ── Курсы ──────────────────────────────────────────────────────────────

class ExchangeRatesResponse(BaseModel):
	"""Курсы валют относительно базовой валюты."""

	base: str = Field(description="Базовая валюта")
	rates: dict[str, Decimal] = Field(description="Курсы: код валюты → значение")
	last_updated: datetime = Field(description="Время последнего обновления курса")


class ExchangeRatePairResponse(BaseModel):
	"""Курс конкретной валютной пары."""

	base: str = Field(description="Базовая валюта")
	target: str = Field(description="Целевая валюта")
	rate: Decimal = Field(description="Курс конвертации")
	last_updated: datetime = Field(description="Время последнего обновления курса")


# ── Обмен между счетами ───────────────────────────────────────────────

class ExchangeRequest(BaseModel):
	"""Запрос на обмен валюты между банковскими счетами (RUB/USD/EUR)."""

	from_account_id: UUID = Field(description="UUID счёта-источника")
	to_account_id: UUID = Field(description="UUID счёта-назначения")
	amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2, description="Сумма в валюте счёта-источника")

	model_config = ConfigDict(extra="forbid")


class ExchangeResponse(BaseModel):
	"""Результат обмена валюты между счетами."""

	message: str = Field(description="Сообщение о результате")
	from_account_id: UUID
	to_account_id: UUID
	from_amount: Decimal = Field(description="Списано со счёта-источника")
	to_amount: Decimal = Field(description="Зачислено на счёт-назначение")
	rate: Decimal = Field(description="Применённый курс")
	from_currency: str
	to_currency: str


__all__ = [
	"ExchangeRatePairResponse",
	"ExchangeRatesResponse",
	"ExchangeRequest",
	"ExchangeResponse",
]
