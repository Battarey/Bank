"""Асинхронный клиент Metals.Dev API для получения цен на драгоценные металлы."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from shared.bootstrap import get_container

from .config import MetalSettings

logger = logging.getLogger("metal_service.client")

def _get_settings() -> MetalSettings:
	"""Получает специфические настройки для сервиса металлов."""
	return get_container().settings


_NAME_TO_CODE = {
	"gold": "XAU",
	"silver": "XAG",
	"platinum": "XPT",
	"palladium": "XPD",
}

# Человекочитаемые названия
METAL_NAMES = {
	"XAU": "Золото",
	"XAG": "Серебро",
	"XPT": "Платина",
	"XPD": "Палладий",
}

_client: httpx.AsyncClient | None = None

# In-memory кэш: base_currency → (prices, last_updated, fetch_timestamp_monotonic)
_cache: dict[str, tuple[dict[str, Decimal], datetime, float]] = {}


async def connect() -> None:
	global _client
	_client = httpx.AsyncClient(timeout=10.0)


async def disconnect() -> None:
	global _client
	if _client is not None:
		await _client.aclose()
		_client = None
		logger.info("Metals.Dev client отключён.")


async def _fetch_prices(currency: str) -> tuple[dict[str, Decimal], datetime]:
	"""Запрашивает цены за грамм у Metals.Dev API."""
	if _client is None:
		raise RuntimeError("Metals.Dev client не инициализирован. Вызовите connect().")

	settings = _get_settings()
	response = await _client.get(
		f"{settings.METALS_DEV_BASE_URL}/latest",
		params={
			"api_key": settings.METALS_DEV_API_KEY,
			"currency": currency,
			"unit": "g",
		},
	)
	response.raise_for_status()
	data: dict[str, Any] = response.json()

	if data.get("status") != "success":
		code = data.get("error_code", "?")
		msg = data.get("error_message", "unknown")
		raise RuntimeError(f"Metals.Dev API error {code}: {msg}")

	raw_metals = data.get("metals", {})
	timestamp_str = data.get("timestamp", "")

	prices: dict[str, Decimal] = {}
	for api_name, iso_code in _NAME_TO_CODE.items():
		raw = raw_metals.get(api_name)
		if raw is not None and raw > 0:
			prices[iso_code] = Decimal(str(raw)).quantize(Decimal("0.01"))
		else:
			logger.warning("Металл %s (%s) отсутствует в ответе API", iso_code, api_name)

	try:
		last_updated = datetime.fromisoformat(timestamp_str)
	except (ValueError, TypeError):
		last_updated = datetime.now(UTC)

	return prices, last_updated


async def get_metal_prices(
	base_currency: str = "RUB",
) -> tuple[dict[str, Decimal], datetime]:
	"""Возвращает цены всех металлов за грамм в указанной валюте."""
	base_currency = base_currency.upper()
	now = time.monotonic()

	cached = _cache.get(base_currency)
	if cached is not None:
		prices, last_updated, fetched_at = cached
		if now - fetched_at < _get_settings().METAL_RATE_CACHE_TTL:
			return prices, last_updated

	prices, last_updated = await _fetch_prices(base_currency)
	_cache[base_currency] = (prices, last_updated, now)
	return prices, last_updated


__all__ = ["METAL_NAMES", "connect", "disconnect", "get_metal_prices"]
