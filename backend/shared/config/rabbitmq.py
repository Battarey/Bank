"""Настройки подключения к RabbitMQ."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RabbitMQSettings(BaseSettings):
	"""Настройки RabbitMQ (aio-pika).

	Attributes:
		APP_ENV: Текущее окружение (local, test, dev, prod).
		URL: Строка подключения к RabbitMQ (amqp://...).
		NOTIFICATIONS_EXCHANGE: Название exchange для уведомлений.
		LOGS_EXCHANGE: Название exchange для системных логов.
		MAX_RETRIES: Максимальное количество попыток переподключения.
		RETRY_DELAY: Задержка между попытками переподключения (в секундах).
	"""

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)

	APP_ENV: str = Field("local", alias="APP_ENV")

	URL: str | None = Field(None, alias="RABBITMQ_URL")
	NOTIFICATIONS_EXCHANGE: str | None = Field(None, alias="NOTIFICATIONS_EXCHANGE")
	LOGS_EXCHANGE: str | None = Field(None, alias="LOGS_EXCHANGE")

	# Параметры retry-логики
	MAX_RETRIES: int = 10
	RETRY_DELAY: int = 3
