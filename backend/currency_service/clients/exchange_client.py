import logging
import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from shared.bootstrap import get_container

logger = logging.getLogger(__name__)


class ExchangeRateClient:
	"""Асинхронный клиент для получения курсов валют через ExchangeRate API.

	Поддерживает два уровня кэширования:
	1. Обычный кэш для информационных целей (CACHE_TTL).
	2. Строгий кэш для торговых операций (TRADE_FRESHNESS_TTL).
	"""

	def __init__(self):
		self._client: httpx.AsyncClient | None = None
		# In-memory кэш: base_currency → (data, fetch_monotonic_time)
		self._cache: dict[str, tuple[dict[str, Any], float]] = {}

	def _get_settings(self) -> Any:
		"""Получает настройки из глобального контейнера."""
		try:
			return get_container().settings
		except Exception:
			from ..core.config import CurrencySettings

			return CurrencySettings()

	async def connect(self) -> None:
		"""Инициализирует HTTP-клиент."""
		if self._client is None:
			self._client = httpx.AsyncClient(timeout=10.0)
			logger.info("ExchangeRate client инициализирован.")

	async def disconnect(self) -> None:
		"""Закрывает ресурсы HTTP-клиента."""
		if self._client is not None:
			await self._client.aclose()
			self._client = None
			logger.info("ExchangeRate client отключён.")

	async def _fetch_rates(self, base: str) -> dict[str, Any]:
		"""Выполняет сетевой запрос к внешнему API."""
		if self._client is None:
			raise RuntimeError("ExchangeRate client не инициализирован. Вызовите connect().")

		settings = self._get_settings()
		url = f"{settings.EXCHANGE_RATE_BASE_URL}/{settings.EXCHANGE_RATE_API_KEY}/latest/{base}"
		
		response = await self._client.get(url)
		response.raise_for_status()
		data = response.json()

		if data.get("result") != "success":
			error_type = data.get("error-type", "unknown")
			raise RuntimeError(f"ExchangeRate API error: {error_type}")

		return data

	async def get_rates(self, base: str) -> tuple[dict[str, Decimal], datetime]:
		"""Возвращает курсы валют (с использованием стандартного кэша)."""
		base = base.upper()
		now = time.monotonic()
		settings = self._get_settings()

		cached = self._cache.get(base)
		if cached is not None:
			data, fetched_at = cached
			if now - fetched_at < settings.CACHE_TTL:
				return self._parse_rates(data)

		data = await self._fetch_rates(base)
		self._cache[base] = (data, now)
		return self._parse_rates(data)

	async def get_fresh_rate(self, base: str, target: str) -> tuple[Decimal, datetime]:
		"""Возвращает актуальный курс для конверсионных операций (строгий кэш).."""
		base = base.upper()
		target = target.upper()
		now = time.monotonic()
		settings = self._get_settings()

		cached = self._cache.get(base)
		if cached is not None:
			data, fetched_at = cached
			if now - fetched_at < settings.TRADE_FRESHNESS_TTL:
				rates, updated = self._parse_rates(data)
				rate = rates.get(target)
				if rate is not None:
					return rate, updated

		data = await self._fetch_rates(base)
		self._cache[base] = (data, now)
		rates, updated = self._parse_rates(data)

		rate = rates.get(target)
		if rate is None:
			raise ValueError(f"Валюта {target} не найдена в ответе API.")
		return rate, updated

	def _parse_rates(self, data: dict[str, Any]) -> tuple[dict[str, Decimal], datetime]:
		"""Преобразует сырой ответ API в формат приложения."""
		raw_rates = data.get("conversion_rates", {})
		rates = {code: Decimal(str(value)) for code, value in raw_rates.items()}

		timestamp = data.get("time_last_update_unix", 0)
		last_updated = datetime.fromtimestamp(timestamp, tz=UTC)

		return rates, last_updated


# Singleton instance для обратной совместимости
_client_instance = ExchangeRateClient()

connect = _client_instance.connect
disconnect = _client_instance.disconnect
get_rates = _client_instance.get_rates
get_fresh_rate = _client_instance.get_fresh_rate

__all__ = ["ExchangeRateClient", "connect", "disconnect", "get_rates", "get_fresh_rate"]
