"""Получение курсов валют из ExchangeRate API."""

import logging
from decimal import Decimal
from datetime import datetime

from currency_service import exchange_client
from currency_service.exceptions import CurrencyNotAvailable, RateUnavailable

logger = logging.getLogger("currency_service")


async def get_all_rates(base: str) -> tuple[dict[str, Decimal], datetime]:
	"""Возвращает все курсы для базовой валюты."""
	try:
		return await exchange_client.get_rates(base)
	except Exception as exc:
		logger.exception("Ошибка получения курсов для %s", base)
		raise RateUnavailable(f"Не удалось получить курсы для {base}: {exc}") from exc


async def get_pair_rate(base: str, target: str) -> tuple[Decimal, datetime]:
	"""Возвращает курс конкретной пары."""
	try:
		rates, updated = await exchange_client.get_rates(base)
	except Exception as exc:
		logger.exception("Ошибка получения курса %s/%s", base, target)
		raise RateUnavailable(f"Не удалось получить курс {base}/{target}: {exc}") from exc

	target = target.upper()
	rate = rates.get(target)
	if rate is None:
		raise CurrencyNotAvailable(f"Валюта {target} не найдена.")
	return rate, updated
