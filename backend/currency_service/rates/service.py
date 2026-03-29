"""Бизнес-логика получения актуальных курсов валют."""

from datetime import datetime
from decimal import Decimal

from .. import exchange_client
from ..exceptions import CurrencyNotAvailable, RateUnavailable


async def get_all_rates(base: str) -> tuple[dict[str, Decimal], datetime]:
	"""Возвращает все доступные курсы обмена для указанной базовой валюты.

	Данные запрашиваются из внешнего API (ExchangeRate) и кэшируются клиентом.

	Args:
		base: Код базовой валюты (например, 'RUB').

	Returns:
		tuple[dict[str, Decimal], datetime]: Словарь курсов и время последнего обновления.

	Raises:
		RateUnavailable: Если не удалось получить данные от внешнего провайдера.
	"""
	try:
		return await exchange_client.get_rates(base)
	except Exception as exc:
		raise RateUnavailable(f"Не удалось получить курсы для {base}: {exc}") from exc


async def get_pair_rate(base: str, target: str) -> tuple[Decimal, datetime]:
	"""Возвращает курс обмена для конкретной валютной пары.

	Args:
		base: Базовая валюта.
		target: Целевая валюта.

	Returns:
		tuple[Decimal, datetime]: Значение курса и время обновления.

	Raises:
		RateUnavailable: Если API недоступно.
		CurrencyNotAvailable: Если целевая валюта не найдена в списке доступных.
	"""
	try:
		rates, updated = await exchange_client.get_rates(base)
	except Exception as exc:
		raise RateUnavailable(f"Не удалось получить курс {base}/{target}: {exc}") from exc

	target_upper = target.upper()
	rate = rates.get(target_upper)
	if rate is None:
		raise CurrencyNotAvailable(f"Валюта {target_upper} не поддерживается или не найдена.")
		
	return rate, updated
