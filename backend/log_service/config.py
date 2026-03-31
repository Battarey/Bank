"""Конфигурация Log Service через Pydantic Settings."""

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
	LOGS_EXCHANGE: str = Field("logs", alias="LOGS_EXCHANGE")
	LOG_QUEUE: str = Field("log_queue", alias="LOG_QUEUE")
	LOG_BINDING_KEY: str = Field("log.#", alias="LOG_BINDING_KEY")

	# PostgreSQL History
	HISTORY_DATABASE_URL: str

	# ClickHouse
	CLICKHOUSE_HOST: str
	CLICKHOUSE_PORT: int = 8123
	CLICKHOUSE_USER: str
	CLICKHOUSE_PASSWORD: str
	CLICKHOUSE_DB: str


settings = Settings()
