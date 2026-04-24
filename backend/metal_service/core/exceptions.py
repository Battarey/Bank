"""Исключения metal_service, интегрированные с глобальным обработчиком."""

from shared.utils.exceptions import (
	BaseBusinessError,
	ExternalServiceError,
)


class MetalError(BaseBusinessError):
	"""Базовая ошибка операций с металлами."""

	title = "Ошибка операций с драгметаллами"


class RateUnavailable(MetalError, ExternalServiceError):
	"""Не удалось получить актуальную цену металла."""

	title = "Цена металла недоступна"
