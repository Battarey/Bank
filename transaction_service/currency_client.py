"""HTTP-клиент для получения курса валют из Currency Service."""

import logging
import os
from decimal import Decimal

import httpx

logger = logging.getLogger("transaction_service")

CURRENCY_SERVICE_URL = os.getenv("CURRENCY_SERVICE_URL", "http://currency_service:8000")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

_client: httpx.AsyncClient | None = None


async def connect() -> None:
	"""Создаёт httpx-клиент для Currency Service."""
	global _client  # noqa: PLW0603
	_client = httpx.AsyncClient(base_url=CURRENCY_SERVICE_URL, timeout=10.0)
	logger.info("Currency client подключён: %s", CURRENCY_SERVICE_URL)


async def disconnect() -> None:
	"""Закрывает httpx-клиент."""
	global _client  # noqa: PLW0603
	if _client is not None:
		await _client.aclose()
		_client = None
		logger.info("Currency client отключён.")


async def get_rate(base: str, target: str) -> Decimal:
	"""Получает актуальный курс валютной пары из Currency Service.

	Returns:
		Курс конвертации base → target.

	Raises:
		RuntimeError: если клиент не инициализирован или сервис недоступен.
	"""
	if _client is None:
		raise RuntimeError("Currency client не инициализирован. Вызовите connect().")

	response = await _client.get(
		f"/rates/{base.upper()}/{target.upper()}",
		headers={"X-Internal-Key": INTERNAL_API_KEY},
	)
	response.raise_for_status()
	data = response.json()
	return Decimal(str(data["rate"]))
