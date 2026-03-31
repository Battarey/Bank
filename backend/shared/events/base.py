"""Базовые классы событий для проекта."""

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
	"""Базовый класс для всех бизнес-событий проекта."""


class NotificationEvent(BaseEvent):
	"""Событие на отправку уведомления."""
	type: str = Field(..., description="Тип уведомления (шаблон)")
	to: str = Field(..., description="Email получателя")
	variables: Dict[str, Any] = Field(default_factory=dict, description="Переменные для шаблона")


class LogEvent(BaseEvent):
	"""Событие на запись бизнес-лога."""
	user_id: Optional[UUID] = Field(None)
	action: str
	service: str
	details: Optional[str] = None
	entity_id: Optional[UUID] = None
	entity_type: Optional[str] = None
	amount: Optional[float] = None
	currency: Optional[str] = None
	status: str = "success"
