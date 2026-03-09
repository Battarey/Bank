"""Единая иерархия исключений metal_service."""


class MetalError(Exception):
	"""Базовая ошибка операций с металлами."""


class RateUnavailable(MetalError):
	"""Не удалось получить актуальную цену металла."""


__all__ = [
	"MetalError",
	"RateUnavailable",
]
