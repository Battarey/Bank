"""Настройки Log Service."""

from pydantic import Field

from shared.config import BaseAppSettings


class LogSettings(BaseAppSettings):
	"""Настройки для сбора и хранения логов (Postgres + ClickHouse)."""

	# Настройки очередей RabbitMQ для логов
	LOGS_EXCHANGE: str = Field("logs", alias="LOGS_EXCHANGE")
	LOG_QUEUE: str = Field("log_queue", alias="LOG_QUEUE")
	LOG_BINDING_KEY: str = Field("log.#", alias="LOG_BINDING_KEY")

	# Веб-сервер для хелсчеков
	HEALTH_PORT: int = Field(8000, alias="HEALTH_PORT")
