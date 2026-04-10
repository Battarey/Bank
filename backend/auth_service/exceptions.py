"""Исключения auth_service, интегрированные с глобальным обработчиком."""

from shared.utils.exceptions import (
	BaseBusinessError,
	ConflictError,
	ForbiddenError,
	NotFoundError,
)


class AuthError(BaseBusinessError):
	"""Базовая ошибка сервиса аутентификации."""

	title = "Ошибка аутентификации"


class AuthNotFound(AuthError, NotFoundError):
	"""Пользователь не найден."""

	title = "Пользователь не найден"


class AuthForbidden(AuthError, ForbiddenError):
	"""Неверный PIN-код или доступ запрещен."""

	title = "Доступ запрещён"


class AuthCooldown(AuthError, ForbiddenError):
	"""Временная блокировка при подборе (rate-limit)."""

	title = "Попробуйте позже"

	def __init__(self, message: str, retry_after: int):
		super().__init__(message, details={"retry_after_seconds": retry_after})


class AuthAlreadyBlocked(AuthError, ConflictError):
	"""Аккаунт уже заблокирован."""

	title = "Аккаунт заблокирован"


class AuthNotBlocked(AuthError, ConflictError):
	"""Аккаунт не заблокирован (для процесса разблокировки)."""

	title = "Аккаунт не заблокирован"


class AuthInvalidCode(AuthError, ForbiddenError):
	"""Неверный код разблокировки."""

	title = "Неверный код"
