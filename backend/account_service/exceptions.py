"""Единая иерархия исключений account_service."""


class AccountError(Exception):
	"""Базовая ошибка операций со счетами."""


class AccountNotFound(AccountError):
	"""Счёт не найден или не принадлежит пользователю."""


class AccountOwnerNotFound(AccountError):
	"""Владелец счёта не найден или не активен."""


class AccountLimitReached(AccountError):
	"""Превышен лимит счетов данного типа/валюты."""


class AccountNotOpen(AccountError):
	"""Счёт не в статусе open — невозможно выполнить операцию."""


class AccountNonZeroBalance(AccountError):
	"""На счёте есть остаток — невозможно закрыть."""


class AccountFrozen(AccountError):
	"""Счёт заморожен — операция невозможна."""


class AccountAlreadyFrozen(AccountError):
	"""Счёт уже заморожен."""


class AccountNotFrozen(AccountError):
	"""Счёт не заморожен — разморозка невозможна."""


class UnfreezeNotAllowed(AccountError):
	"""Разморозка невозможна — счёт заморожен системой."""


class AccountConflict(AccountError):
	"""Конфликт данных (например, дублирование номера счёта)."""


__all__ = [
	"AccountAlreadyFrozen",
	"AccountConflict",
	"AccountError",
	"AccountFrozen",
	"AccountLimitReached",
	"AccountNonZeroBalance",
	"AccountNotFound",
	"AccountNotFrozen",
	"AccountNotOpen",
	"AccountOwnerNotFound",
	"UnfreezeNotAllowed",
]
