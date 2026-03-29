"""Исключения security_service, интегрированные с глобальным обработчиком."""

from shared.utils.exceptions import (
	BaseBusinessError,
	NotFoundError,
)


class SecurityError(BaseBusinessError):
	"""Базовая ошибка сервиса безопасности."""
	title = "Ошибка безопасности"


class AccountNotFound(SecurityError, NotFoundError):
	"""Счёт не найден в базе данных."""
	title = "Счёт не найден"
