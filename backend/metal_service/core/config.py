"""Настройки Metal Service."""

from pydantic import Field

from shared.config import BaseAppSettings


class MetalSettings(BaseAppSettings):
	"""Настройки для работы с котировками металлов и Metals.Dev API."""

	# API Ключ и URL провайдера (Metals.Dev)
	METALS_DEV_API_KEY: str = Field(..., alias="METALS_DEV_API_KEY")
	METALS_DEV_BASE_URL: str = Field("https://api.metals.dev/v1", alias="METALS_DEV_BASE_URL")

	# Настройки кэширования (в секундах)
	METAL_RATE_CACHE_TTL: int = Field(30, alias="METAL_RATE_CACHE_TTL")
