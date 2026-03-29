"""Исключения transaction_service, интегрированные с глобальным обработчиком."""

from shared.utils.exceptions import (
	BaseBusinessError,
	ConflictError,
	ForbiddenError,
	NotFoundError,
	UnprocessableError,
)


class TransactionError(BaseBusinessError):
	"""Базовая ошибка транзакционных операций."""
	title = "Ошибка транзакции"


class AccountNotFound(TransactionError, NotFoundError):
	"""Счёт не найден или не принадлежит пользователю."""
	title = "Счёт не найден"


class AccountNotOpen(TransactionError, UnprocessableError):
	"""Счёт не в статусе open — операция невозможна."""
	title = "Счёт не активен"


class AccountFrozen(TransactionError, ForbiddenError):
	"""Счёт заморожен — исходящие операции запрещены."""
	title = "Счёт заморожен"


class SecurityViolation(TransactionError, ForbiddenError):
	"""Операция отклонена антифрод-системой."""
	title = "Операция отклонена безопасностью"


class InsufficientFunds(TransactionError, UnprocessableError):
	"""Недостаточно средств на счёте."""
	title = "Недостаточно средств"


class SameAccountTransfer(TransactionError, UnprocessableError):
	"""Попытка перевода на тот же счёт."""
	title = "Перевод самому себе"


class CurrencyMismatch(TransactionError, UnprocessableError):
	"""Валюты счетов не совпадают."""
	title = "Несоответствие валют"


class RateUnavailable(TransactionError, UnprocessableError):
	"""Не удалось получить актуальный курс валют."""
	title = "Курс валют недоступен"


class TransactionConflict(TransactionError, ConflictError):
	"""Конфликт данных (IntegrityError)."""
	title = "Конфликт данных"
