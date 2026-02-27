"""Схемы аутентификации."""

from typing import Annotated

from pydantic import BaseModel, Field


# ── Общие типы ─────────────────────────────────────────────────────────

Phone = Annotated[str, Field(pattern=r"^\+7\d{10}$")]
Pin = Annotated[str, Field(pattern=r"^\d{4,6}$")]


# ── Вход по PIN ────────────────────────────────────────────────────────

class LoginPinRequest(BaseModel):
	phone: Phone
	pin: Pin


class LoginPinResponse(BaseModel):
	session_token: str
	user_id: str


# ── Установка PIN ──────────────────────────────────────────────────────

class SetPinRequest(BaseModel):
	pin: Pin


class MessageResponse(BaseModel):
	message: str
