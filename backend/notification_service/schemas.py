"""Pydantic-схемы для Notification Service."""

from typing import Any, Dict
from pydantic import BaseModel, Field, EmailStr


class NotificationPayload(BaseModel):
	"""Полезная нагрузка уведомления."""
	to: EmailStr = Field(..., description="Email получателя")
	variables: Dict[str, Any] = Field(default_factory=dict, description="Переменные для шаблона")


class NotificationTask(BaseModel):
	"""Входящее задание на отправку уведомления из RabbitMQ."""
	type: str = Field(..., description="Тип уведомления (имя шаблона)")
	payload: NotificationPayload
