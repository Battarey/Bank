"""Конфигурация Notification Service через Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	"""Настройки приложения, загружаемые из .env."""

	model_config = SettingsConfigDict(
		env_file=".env", 
		env_file_encoding="utf-8", 
		extra="ignore"
	)

	# RabbitMQ
	RABBIT_URL: str = Field(alias="RABBITMQ_URL")
	NOTIFICATIONS_EXCHANGE: str = Field("notifications", alias="NOTIFICATIONS_EXCHANGE")
	EMAIL_QUEUE: str = Field("email_queue", alias="EMAIL_QUEUE")
	EMAIL_BINDING_KEY: str = Field("email.#", alias="EMAIL_BINDING_KEY")

	# MongoDB
	MONGO_URL: str

	# SMTP
	SMTP_HOST: str
	SMTP_PORT: int = 465
	SMTP_USER: str
	SMTP_PASSWORD: str
	SMTP_FROM: str | None = None
	SMTP_USE_TLS: bool = True

	@property
	def smtp_from_addr(self) -> str:
		"""Возвращает адрес отправителя (SMTP_FROM или SMTP_USER)."""
		return self.SMTP_FROM or self.SMTP_USER


settings = Settings()
