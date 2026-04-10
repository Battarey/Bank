"""Pydantic-схемы для Log Service."""

from datetime import datetime, UTC
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class LogPayload(BaseModel):
	"""Полезная нагрузка лога."""
	user_id: Optional[UUID] = Field(None, description="ID пользователя")
	action: str = Field(..., description="Действие (например, transfer, deposit)")
	service: str = Field(..., description="Имя сервиса-источника")
	details: Optional[str] = Field(None, description="Дополнительные детали")
	entity_id: Optional[UUID] = Field(None, description="ID связанной сущности (транзакции, счета)")
	entity_type: Optional[str] = Field(None, description="Тип сущности")
	amount: Optional[float] = Field(None, description="Сумма (для финансовых операций)")
	currency: Optional[str] = Field(None, description="Валюта")
	status: str = Field("success", description="Статус операции")
	ip_address: Optional[str] = Field(None, description="IP-адрес")
	created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LogEvent(BaseModel):
	"""Входящее событие логирования из RabbitMQ."""
	type: str = Field(..., description="Тип события")
	payload: LogPayload
