"""Единая иерархия исключений transaction_service."""


class TransactionError(Exception):
	"""Базовая ошибка транзакционных операций."""


class AccountNotFound(TransactionError):
	"""Счёт не найден или не принадлежит пользователю."""


class AccountNotOpen(TransactionError):
	"""Счёт не в статусе open — операция невозможна."""


class InsufficientFunds(TransactionError):
	"""Недостаточно средств на счёте."""


class SameAccountTransfer(TransactionError):
	"""Попытка перевода на тот же счёт."""


class CurrencyMismatch(TransactionError):
	"""Валюты счетов не совпадают (конвертация не поддерживается)."""


class TransactionConflict(TransactionError):
	"""Конфликт данных (IntegrityError)."""


__all__ = [
	"AccountNotFound",
	"AccountNotOpen",
	"CurrencyMismatch",
	"InsufficientFunds",
	"SameAccountTransfer",
	"TransactionConflict",
	"TransactionError",
]
