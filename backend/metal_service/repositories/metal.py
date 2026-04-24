"""Репозиторий для получения котировок металлов из внешних источников."""

import asyncio
import logging
import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from shared.bootstrap import get_container

from ..core.config import MetalSettings
from ..core.exceptions import RateUnavailable

logger = logging.getLogger("metal_service.repository")


class MetalRepository:
	"""Репозиторий для работы с Metals.Dev API.

	Обеспечивает получение цен и потокобезопасное кэширование.
	"""

	_NAME_TO_CODE = {
		"gold": "XAU",
		"silver": "XAG",
		"platinum": "XPT",
		"palladium": "XPD",
	}

	def __init__(self):
		self._client: httpx.AsyncClient | None = None
		# base_currency -> (prices, last_updated, fetch_timestamp_monotonic)
		self._cache: dict[str, tuple[dict[str, Decimal], datetime, float]] = {}
		self._lock = asyncio.Lock()

	async def connect(self) -> None:
		"""Инициализация HTTP-клиента."""
		if self._client is None:
			self._client = httpx.AsyncClient(timeout=10.0)

	async def disconnect(self) -> None:
		"""Закрытие HTTP-клиента."""
		if self._client is not None:
			await self._client.aclose()
			self._client = None

	@property
	def _settings(self) -> MetalSettings:
		return get_container().settings

	async def _fetch_from_api(self, currency: str) -> tuple[dict[str, Decimal], datetime]:
		"""Запрос данных напрямую из Metals.Dev API."""
		if self._client is None:
			await self.connect()

		try:
			response = await self._client.get(
				f"{self._settings.METALS_DEV_BASE_URL}/latest",
				params={
					"api_key": self._settings.METALS_DEV_API_KEY,
					"currency": currency,
					"unit": "g",
				},
			)
			response.raise_for_status()
			data: dict[str, Any] = response.json()

			if data.get("status") != "success":
				code = data.get("error_code", "?")
				msg = data.get("error_message", "unknown")
				raise RateUnavailable(f"Metals.Dev API error {code}: {msg}")

			raw_metals = data.get("metals", {})
			timestamp_str = data.get("timestamp", "")

			prices: dict[str, Decimal] = {}
			for api_name, iso_code in self._NAME_TO_CODE.items():
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

		except httpx.HTTPError as exc:
			raise RateUnavailable(f"Ошибка сети при запросе котировок: {exc}") from exc

	async def get_metal_prices(self, base_currency: str) -> tuple[dict[str, Decimal], datetime]:
		"""Возвращает цены металлов с использованием потокобезопасного кэша."""
		base_currency = base_currency.upper()
		now = time.monotonic()

		# Быстрая проверка кэша без блокировки
		cached = self._cache.get(base_currency)
		if cached:
			prices, last_updated, fetched_at = cached
			if now - fetched_at < self._settings.METAL_RATE_CACHE_TTL:
				return prices, last_updated

		# Если кэша нет или он протух — запрашиваем с блокировкой
		async with self._lock:
			# Double-check после захвата лока
			cached = self._cache.get(base_currency)
			if cached:
				prices, last_updated, fetched_at = cached
				if now - fetched_at < self._settings.METAL_RATE_CACHE_TTL:
					return prices, last_updated

			prices, last_updated = await self._fetch_from_api(base_currency)
			self._cache[base_currency] = (prices, last_updated, now)
			return prices, last_updated


# Синглтон репозитория для использования в Depends
_repository = MetalRepository()


def get_metal_repository() -> MetalRepository:
	"""Провайдер репозитория для FastAPI Depends."""
	return _repository
