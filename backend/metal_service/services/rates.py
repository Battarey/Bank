"""Бизнес-логика получения котировок драгоценных металлов."""

from datetime import datetime
from decimal import Decimal

from ..clients import metal_client
from ..core.exceptions import RateUnavailable


async def get_all_prices(base_currency: str) -> tuple[dict[str, Decimal], datetime]:
	"""Возвращает актуальные цены всех поддерживаемых металлов за грамм.

	Данные запрашиваются из внешнего API (через MetalClient) и кэшируются.

	Args:
		base_currency: Код базовой валюты (например, 'RUB').

	Returns:
		tuple[dict[str, Decimal], datetime]: Словарь цен (металл -> цена) и время обновления.

	Raises:
		RateUnavailable: Если не удалось получить данные от внешнего провайдера.
	"""
	try:
		return await metal_client.get_metal_prices(base_currency)
	except Exception as exc:
		raise RateUnavailable(f"Не удалось получить цены металлов для {base_currency}: {exc}") from exc
