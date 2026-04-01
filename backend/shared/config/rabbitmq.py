"""Настройки подключения к RabbitMQ."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RabbitMQSettings(BaseSettings):
	"""Настройки RabbitMQ (aio-pika)."""

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)

	URL: str = Field(..., alias="RABBITMQ_URL")
	
	# Каналы уведомлений и логов (Exchanges) (ОБЯЗАТЕЛЬНЫ к заполнению)
	NOTIFICATIONS_EXCHANGE: str = Field(..., alias="NOTIFICATIONS_EXCHANGE")
	LOGS_EXCHANGE: str = Field(..., alias="LOGS_EXCHANGE")

	# Параметры retry-логики
	MAX_RETRIES: int = 10
	RETRY_DELAY: int = 3
