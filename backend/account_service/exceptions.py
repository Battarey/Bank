"""Исключения account_service, интегрированные с глобальным обработчиком."""

from shared.utils.exceptions import (
	BaseBusinessError,
	ConflictError,
	ForbiddenError,
	NotFoundError,
	UnprocessableError,
)


class AccountError(BaseBusinessError):
	"""Базовая ошибка операций со счетами."""
	title = "Ошибка банковского счёта"


class AccountNotFound(AccountError, NotFoundError):
	"""Счёт не найден или не принадлежит пользователю."""
	title = "Счёт не найден"


class AccountOwnerNotFound(AccountError, NotFoundError):
	"""Владелец счёта не найден или не активен."""
	title = "Владелец не найден"


class AccountLimitReached(AccountError, ForbiddenError):
	"""Превышен лимит счетов данного типа/валюты."""
	title = "Лимит счетов превышен"


class AccountNotOpen(AccountError, UnprocessableError):
	"""Счёт не в статусе open — невозможно выполнить операцию."""
	title = "Счёт недоступен"


class AccountNonZeroBalance(AccountError, ConflictError):
	"""На счёте есть остаток — невозможно закрыть."""
	title = "Баланс не нулевой"


class AccountFrozen(AccountError, ForbiddenError):
	"""Счёт заморожен — операция невозможна."""
	title = "Счёт заморожен"


class AccountAlreadyFrozen(AccountError, ConflictError):
	"""Счёт уже заморожен."""
	title = "Счёт уже заморожен"


class AccountNotFrozen(AccountError, ConflictError):
	"""Счёт не заморожен — разморозка невозможна."""
	title = "Счёт не заморожен"


class UnfreezeNotAllowed(AccountError, ForbiddenError):
	"""Разморозка невозможна — счёт заморожен системой."""
	title = "Разморозка запрещена"


class AccountConflict(AccountError, ConflictError):
	"""Конфликт данных (например, дублирование номера счёта)."""
	title = "Конфликт данных"
