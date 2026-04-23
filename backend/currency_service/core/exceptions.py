"""Исключения currency_service, интегрированные с глобальным обработчиком."""

from shared.utils.exceptions import (
	BaseBusinessError,
	NotFoundError,
	UnprocessableError,
)


class CurrencyError(BaseBusinessError):
	"""Базовая ошибка валютных операций."""

	title = "Ошибка валютных операций"


class AccountNotFound(CurrencyError, NotFoundError):
	"""Счёт не найден или не принадлежит пользователю."""

	title = "Счёт не найден"


class AccountNotOpen(CurrencyError, UnprocessableError):
	"""Счёт не в статусе open."""

	title = "Счёт недоступен"


class InsufficientFunds(CurrencyError, UnprocessableError):
	"""Недостаточно средств на счёте."""

	title = "Недостаточно средств"


class SameAccountExchange(CurrencyError, UnprocessableError):
	"""Попытка обмена на тот же счёт."""

	title = "Обмен на тот же счёт"


class SameCurrencyExchange(CurrencyError, UnprocessableError):
	"""Валюты совпадают — обмен не нужен."""

	title = "Валюты совпадают"


class CurrencyNotAvailable(CurrencyError, NotFoundError):
	"""Валюта недоступна в API."""

	title = "Валюта недоступна"


class RateUnavailable(CurrencyError):
	"""Не удалось получить актуальный курс."""

	status_code = 502
	title = "Курс валют недоступен"
