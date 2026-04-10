"""Конфигурация Notification Service через Pydantic Settings."""

from pydantic import Field

from shared.config import BaseAppSettings


class NotificationSettings(BaseAppSettings):
	"""Настройки для отправки уведомлений (RabbitMQ + SMTP + MongoDB)."""

	# RabbitMQ
	RABBITMQ_URL: str = Field(..., alias="RABBITMQ_URL")
	NOTIFICATIONS_EXCHANGE: str = Field("notifications", alias="NOTIFICATIONS_EXCHANGE")
	EMAIL_QUEUE: str = Field("email_queue", alias="EMAIL_QUEUE")
	EMAIL_BINDING_KEY: str = Field("email.#", alias="EMAIL_BINDING_KEY")

	# MongoDB (Хранение истории)
	MONGO_URL: str = Field(..., alias="MONGO_URL")

	# SMTP (Email)
	SMTP_HOST: str = Field(..., alias="SMTP_HOST")
	SMTP_PORT: int = Field(465, alias="SMTP_PORT")
	SMTP_USER: str = Field(..., alias="SMTP_USER")
	SMTP_PASSWORD: str = Field(..., alias="SMTP_PASSWORD")
	SMTP_FROM: str | None = Field(None, alias="SMTP_FROM")
	SMTP_USE_TLS: bool = Field(True, alias="SMTP_USE_TLS")

	@property
	def smtp_from_addr(self) -> str:
		"""Возвращает адрес отправителя (SMTP_FROM или SMTP_USER)."""
		return self.SMTP_FROM or self.SMTP_USER
