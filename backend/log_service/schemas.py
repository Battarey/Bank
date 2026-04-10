"""Pydantic-схемы для Log Service."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LogPayload(BaseModel):
	"""Полезная нагрузка лога."""
	user_id: UUID | None = Field(None, description="ID пользователя")
	action: str = Field(..., description="Действие (например, transfer, deposit)")
	service: str = Field(..., description="Имя сервиса-источника")
	details: str | None = Field(None, description="Дополнительные детали")
	entity_id: UUID | None = Field(None, description="ID связанной сущности (транзакции, счета)")
	entity_type: str | None = Field(None, description="Тип сущности")
	amount: float | None = Field(None, description="Сумма (для финансовых операций)")
	currency: str | None = Field(None, description="Валюта")
	status: str = Field("success", description="Статус операции")
	ip_address: str | None = Field(None, description="IP-адрес")
	created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LogEvent(BaseModel):
	"""Входящее событие логирования из RabbitMQ."""
	type: str = Field(..., description="Тип события")
	payload: LogPayload
