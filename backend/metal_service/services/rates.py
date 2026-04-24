"""Бизнес-логика получения котировок драгоценных металлов."""

import re
from datetime import datetime
from decimal import Decimal

from fastapi import Depends

from shared.utils.exceptions import UnprocessableError

from ..repositories.metal import MetalRepository, get_metal_repository


class MetalRatesService:
	"""Сервис для работы с котировками металлов."""

	def __init__(self, repository: MetalRepository = Depends(get_metal_repository)):
		self._repository = repository

	async def get_all_prices(self, base_currency: str) -> tuple[dict[str, Decimal], datetime]:
		"""Возвращает актуальные цены металлов за грамм.

		Args:
			base_currency: Код базовой валюты (ISO 4217).

		Returns:
			tuple[dict[str, Decimal], datetime]: Цены и время обновления.

		Raises:
			UnprocessableError: Если код валюты невалиден.
			RateUnavailable: Если данные недоступны.
		"""
		self._validate_currency(base_currency)
		return await self._repository.get_metal_prices(base_currency)

	def _validate_currency(self, currency: str) -> None:
		"""Проверка формата кода валюты."""
		if not re.match(r"^[A-Z]{3}$", currency):
			raise UnprocessableError(
				message=f"Некорректный формат валюты: {currency}. Ожидается 3-буквенный ISO код.",
				details={"currency": currency}
			)


def get_metal_rates_service(
	service: MetalRatesService = Depends(MetalRatesService)
) -> MetalRatesService:
	"""Провайдер сервиса для FastAPI Depends."""
	return service
