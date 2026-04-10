"""Исключения customer_service, интегрированные с глобальным обработчиком."""

from shared.utils.exceptions import (
	BaseBusinessError,
	ConflictError,
	NotFoundError,
	UnprocessableError,
)


class CustomerError(BaseBusinessError):
	"""Базовое исключение для сервиса клиентов."""

	title = "Ошибка сервиса клиентов"


# ── Онбординг (создание аккаунта) ─────────────────────────────────────


class OnboardingError(CustomerError):
	"""Ошибка данных онбординга."""


class OnboardingNotFound(OnboardingError, NotFoundError):
	"""Данные онбординга не найдены в Redis."""

	title = "Черновик не найден"


class OnboardingConflict(OnboardingError, ConflictError):
	"""Данные конфликтуют с существующим пользователем."""

	title = "Конфликт данных при регистрации"


# ── Обновление данных ─────────────────────────────────────────────────


class UpdateDataError(CustomerError):
	"""Ошибка при обновлении профиля."""


class UpdateDataNotFound(UpdateDataError, NotFoundError):
	"""Профиль не найден."""

	title = "Пользователь не найден"


class UpdateDataConflict(UpdateDataError, ConflictError):
	"""Конфликт уникальности (email/phone)."""

	title = "Контактные данные уже используются"


class UpdateDataEmpty(UpdateDataError, UnprocessableError):
	"""Пустой запрос на обновление."""

	title = "Нет данных для обновления"


# ── Удаление аккаунта ─────────────────────────────────────────────────


class DeleteAccountError(CustomerError):
	"""Ошибка при удалении аккаунта."""


class AccountNotFound(DeleteAccountError, NotFoundError):
	"""Аккаунт не найден."""

	title = "Аккаунт не найден"


class AccountAlreadyDeleted(DeleteAccountError, ConflictError):
	"""Аккаунт уже удалён."""

	title = "Аккаунт уже в статусе deleted"
