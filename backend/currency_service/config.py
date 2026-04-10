"""Настройки Currency Service."""

from pydantic import Field

from shared.config import BaseAppSettings


class CurrencySettings(BaseAppSettings):
	"""Настройки для работы с курсами валют и внешним API."""

	# API Ключ и URL провайдера (ExchangeRate-API)
	EXCHANGE_RATE_API_KEY: str = Field(..., alias="EXCHANGE_RATE_API_KEY")
	EXCHANGE_RATE_BASE_URL: str = Field(
		"https://v6.exchangerate-api.com/v6", 
		alias="EXCHANGE_RATE_BASE_URL"
	)

	# Настройки кэширования (в секундах)
	CACHE_TTL: int = Field(30, alias="EXCHANGE_RATE_CACHE_TTL")
	TRADE_FRESHNESS_TTL: int = Field(60, alias="EXCHANGE_RATE_TRADE_TTL")
