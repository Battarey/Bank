"""Pydantic-схемы для Notification Service."""

from typing import Any

from pydantic import BaseModel, EmailStr, Field


class NotificationPayload(BaseModel):
	"""Полезная нагрузка уведомления."""

	to: EmailStr = Field(..., description="Email получателя")
	variables: dict[str, Any] = Field(default_factory=dict, description="Переменные для шаблона")


class NotificationTask(BaseModel):
	"""Входящее задание на отправку уведомления из RabbitMQ."""

	type: str = Field(..., description="Тип уведомления (имя шаблона)")
	payload: NotificationPayload
