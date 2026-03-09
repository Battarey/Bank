"""Единая иерархия исключений currency_service."""


class CurrencyError(Exception):
	"""Базовая ошибка валютных операций."""


class AccountNotFound(CurrencyError):
	"""Счёт не найден или не принадлежит пользователю."""


class AccountNotOpen(CurrencyError):
	"""Счёт не в статусе open."""


class InsufficientFunds(CurrencyError):
	"""Недостаточно средств на счёте."""


class SameAccountExchange(CurrencyError):
	"""Попытка обмена на тот же счёт."""


class SameCurrencyExchange(CurrencyError):
	"""Валюты совпадают — обмен не нужен."""


class CurrencyNotAvailable(CurrencyError):
	"""Валюта недоступна в API."""


class RateUnavailable(CurrencyError):
	"""Не удалось получить актуальный курс."""


__all__ = [
	"AccountNotFound",
	"AccountNotOpen",
	"CurrencyError",
	"CurrencyNotAvailable",
	"InsufficientFunds",
	"RateUnavailable",
	"SameAccountExchange",
	"SameCurrencyExchange",
]
