"""Асинхронный клиент ExchangeRate API с in-memory кэшированием."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from shared.bootstrap import get_container

logger = logging.getLogger(__name__)


def _get_settings() -> Any:
	"""Получает специфические настройки для сервиса валют."""
	try:
		return get_container().settings
	except Exception:
		# fallback для тестов, если контейнер не инициализирован
		from ..core.config import CurrencySettings

		return CurrencySettings()


_client: httpx.AsyncClient | None = None

# In-memory кэш: base_currency → (data, fetch_timestamp)
_cache: dict[str, tuple[dict[str, Any], float]] = {}


async def connect() -> None:
	"""Создаёт httpx-клиент."""
	global _client
	_client = httpx.AsyncClient(timeout=10.0)


async def disconnect() -> None:
	"""Закрывает httpx-клиент."""
	global _client
	if _client is not None:
		await _client.aclose()
		_client = None
		logger.info("ExchangeRate client отключён.")


async def _fetch_rates(base: str) -> dict[str, Any]:
	"""Запрашивает курсы у ExchangeRate API."""
	if _client is None:
		raise RuntimeError("ExchangeRate client не инициализирован. Вызовите connect().")

	settings = _get_settings()
	url = f"{settings.EXCHANGE_RATE_BASE_URL}/{settings.EXCHANGE_RATE_API_KEY}/latest/{base}"
	response = await _client.get(url)
	response.raise_for_status()
	data = response.json()

	if data.get("result") != "success":
		error_type = data.get("error-type", "unknown")
		raise RuntimeError(f"ExchangeRate API error: {error_type}")

	return data


async def get_rates(base: str) -> tuple[dict[str, Decimal], datetime]:
	"""Возвращает курсы валют для базовой валюты (с кэшированием).

	Returns:
		(rates_dict, last_updated) — словарь {код: курс}, время обновления.
	"""
	base = base.upper()
	now = time.monotonic()

	# Проверяем кэш
	cached = _cache.get(base)
	if cached is not None:
		data, fetched_at = cached
		if now - fetched_at < _get_settings().CACHE_TTL:
			return _parse_rates(data)

	# Кэш устарел или отсутствует — запрашиваем API
	data = await _fetch_rates(base)
	_cache[base] = (data, now)
	return _parse_rates(data)


async def get_fresh_rate(base: str, target: str) -> tuple[Decimal, datetime]:
	"""Возвращает актуальный курс для торговой операции.

	Гарантирует, что данные не старше TRADE_FRESHNESS_TTL секунд.
	Если кэш устарел — запрашивает API заново.

	Returns:
		(rate, last_updated)
	"""
	base = base.upper()
	target = target.upper()
	now = time.monotonic()

	cached = _cache.get(base)
	if cached is not None:
		data, fetched_at = cached
		if now - fetched_at < _get_settings().TRADE_FRESHNESS_TTL:
			rates, updated = _parse_rates(data)
			rate = rates.get(target)
			if rate is not None:
				return rate, updated

	# Принудительно обновляем
	data = await _fetch_rates(base)
	_cache[base] = (data, now)
	rates, updated = _parse_rates(data)

	rate = rates.get(target)
	if rate is None:
		raise ValueError(f"Валюта {target} не найдена в курсах API.")
	return rate, updated


def _parse_rates(data: dict[str, Any]) -> tuple[dict[str, Decimal], datetime]:
	"""Парсит ответ API в (rates_dict, last_updated)."""
	raw_rates = data.get("conversion_rates", {})
	rates = {code: Decimal(str(value)) for code, value in raw_rates.items()}

	timestamp = data.get("time_last_update_unix", 0)
	last_updated = datetime.fromtimestamp(timestamp, tz=UTC)

	return rates, last_updated


__all__ = ["connect", "disconnect", "get_fresh_rate", "get_rates"]
