"""Pydantic-схемы для сервиса драгоценных металлов."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class MetalRateResponse(BaseModel):
	"""Цена одного металла."""

	metal: str = Field(description="Код металла: XAU (золото), XAG (серебро), XPT (платина), XPD (палладий)")
	price_per_gram: Decimal = Field(description="Цена за грамм")
	base_currency: str = Field(description="Валюта цены")
	last_updated: datetime = Field(description="Время последнего обновления")


class MetalRatesListResponse(BaseModel):
	"""Список цен на металлы."""

	rates: list[MetalRateResponse] = Field(description="Массив цен")
	base_currency: str
	last_updated: datetime


__all__ = [
	"MetalRateResponse",
	"MetalRatesListResponse",
]
