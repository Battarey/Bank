"""Исключения metal_service, интегрированные с глобальным обработчиком."""

from shared.utils.exceptions import (
	BaseBusinessError,
	UnprocessableError,
)


class MetalError(BaseBusinessError):
	"""Базовая ошибка операций с металлами."""

	title = "Ошибка операций с драгметаллами"


class RateUnavailable(MetalError, UnprocessableError):
	"""Не удалось получить актуальную цену металла."""

	title = "Цена металла недоступна"
