"""Получение цен на драгоценные металлы."""

import logging
from decimal import Decimal
from datetime import datetime

from metal_service import metal_client
from metal_service.exceptions import RateUnavailable

logger = logging.getLogger("metal_service")


async def get_all_prices(base_currency: str) -> tuple[dict[str, Decimal], datetime]:
	"""Возвращает цены всех металлов за грамм."""
	try:
		return await metal_client.get_metal_prices(base_currency)
	except Exception as exc:
		logger.exception("Ошибка получения цен металлов (base=%s)", base_currency)
		raise RateUnavailable(f"Не удалось получить цены металлов: {exc}") from exc
