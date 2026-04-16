"""Схемы аутентификации."""

from typing import Annotated

from pydantic import BaseModel, Field

# ── Общие типы ─────────────────────────────────────────────────────────

Phone = Annotated[str, Field(pattern=r"^\+7\d{10}$", description="Номер телефона в формате +7XXXXXXXXXX")]
Pin = Annotated[str, Field(pattern=r"^\d{4,6}$", description="PIN-код: от 4 до 6 цифр")]


# ── Вход по PIN ────────────────────────────────────────────────────────


class LoginPinRequest(BaseModel):
	"""Запрос на вход по PIN-коду."""

	phone: Phone
	pin: Pin


class LoginPinResponse(BaseModel):
	"""Ответ на успешный вход: сессионный токен и идентификатор пользователя."""

	session_token: str = Field(description="Сессионный токен (TTL 30 мин)")
	refresh_token: str = Field(description="Токен привязки для быстрого входа (TTL 30 дней)")
	user_id: str = Field(description="UUID пользователя")


# ── Быстрый вход (Quick Login) ──────────────────────────────────────────


class QuickLoginRequest(BaseModel):
	"""Запрос на вход по PIN-коду с использованием токена привязки."""

	refresh_token: str = Field(description="Токен привязки, полученный при первом входе")
	pin: Pin


# ── Установка PIN ──────────────────────────────────────────────────────


class SetPinRequest(BaseModel):
	"""Запрос на установку или смену PIN-кода."""

	pin: Pin


class MessageResponse(BaseModel):
	"""Универсальный текстовый ответ."""

	message: str = Field(description="Текст сообщения")
