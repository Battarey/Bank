"""Единая иерархия исключений transaction_service."""


class TransactionError(Exception):
	"""Базовая ошибка транзакционных операций."""


class AccountNotFound(TransactionError):
	"""Счёт не найден или не принадлежит пользователю."""


class AccountNotOpen(TransactionError):
	"""Счёт не в статусе open — операция невозможна."""


class AccountFrozen(TransactionError):
	"""Счёт заморожен — исходящие операции запрещены."""


class SecurityViolation(TransactionError):
	"""Операция отклонена антифрод-системой."""


class InsufficientFunds(TransactionError):
	"""Недостаточно средств на счёте."""


class SameAccountTransfer(TransactionError):
	"""Попытка перевода на тот же счёт."""


class CurrencyMismatch(TransactionError):
	"""Валюты счетов не совпадают (конвертация не поддерживается)."""


class TransactionConflict(TransactionError):
	"""Конфликт данных (IntegrityError)."""


__all__ = [
	"AccountFrozen",
	"AccountNotFound",
	"AccountNotOpen",
	"CurrencyMismatch",
	"InsufficientFunds",
	"SameAccountTransfer",
	"SecurityViolation",
	"TransactionConflict",
	"TransactionError",
]
