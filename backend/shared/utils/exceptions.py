"""Базовые классы исключений для реализации единой обработки ошибок."""

from typing import Any


class BaseBusinessError(Exception):
	"""Базовый класс для всех бизнес-исключений приложения.

	Все доменные исключения (например, AccountNotFound) должны наследоваться
	от этого класса, чтобы попадать под действие глобального обработчика.
	"""

	status_code: int = 400
	title: str = "Ошибка бизнес-логики"

	def __init__(self, message: str, details: dict[str, Any] | None = None):
		super().__init__(message)
		self.message = message
		self.details = details or {}


class NotFoundError(BaseBusinessError):
	"""Исключение для случаев, когда ресурс не найден."""
	status_code = 404
	title = "Ресурс не найден"


class ConflictError(BaseBusinessError):
	"""Исключение для конфликтов данных (например, дубликаты)."""
	status_code = 409
	title = "Конфликт данных"


class ForbiddenError(BaseBusinessError):
	"""Исключение для нарушения прав доступа или бизнес-правил."""
	status_code = 403
	title = "Действие запрещено"


class UnprocessableError(BaseBusinessError):
	"""Исключение для ошибок валидации бизнес-логики (не Pydantic)."""
	status_code = 422
	title = "Невозможно обработать операцию"
