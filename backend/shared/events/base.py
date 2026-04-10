"""Базовые классы событий для проекта."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
	"""Базовый класс для всех бизнес-событий проекта."""


class NotificationEvent(BaseEvent):
	"""Событие на отправку уведомления."""
	type: str = Field(..., description="Тип уведомления (шаблон)")
	to: str = Field(..., description="Email получателя")
	variables: dict[str, Any] = Field(default_factory=dict, description="Переменные для шаблона")


class LogEvent(BaseEvent):
	"""Событие на запись бизнес-лога."""
	user_id: UUID | None = Field(None)
	action: str
	service: str
	details: str | None = None
	entity_id: UUID | None = None
	entity_type: str | None = None
	amount: float | None = None
	currency: str | None = None
	status: str = "success"
