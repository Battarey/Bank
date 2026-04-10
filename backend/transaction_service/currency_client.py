"""HTTP-клиент для получения курса валют из Currency Service."""

import logging
from decimal import Decimal

import httpx

logger = logging.getLogger("transaction_service")

from shared.bootstrap import get_container

from .config import TransactionSettings


def _get_settings() -> TransactionSettings:
	"""Получает специфические настройки для сервиса транзакций."""
	return get_container().settings


_client: httpx.AsyncClient | None = None


async def connect() -> None:
	"""Создаёт httpx-клиент для Currency Service."""
	global _client
	settings = _get_settings()
	_client = httpx.AsyncClient(base_url=settings.CURRENCY_SERVICE_URL, timeout=10.0)
	logger.info("Currency client подключён: %s", settings.CURRENCY_SERVICE_URL)


async def disconnect() -> None:
	"""Закрывает httpx-клиент."""
	global _client
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

	settings = _get_settings()
	try:
		response = await _client.get(
			f"/rates/{base.upper()}/{target.upper()}",
			headers={"X-Internal-Key": settings.INTERNAL_API_KEY},
		)
		response.raise_for_status()
	except Exception as exc:
		logger.error("ConnectError to Currency Service at %s: %s", settings.CURRENCY_SERVICE_URL, exc)
		raise
	data = response.json()
	return Decimal(str(data["rate"]))
