"""Настройки Log Service."""

from pydantic import Field

from shared.config import BaseAppSettings


class LogSettings(BaseAppSettings):
	"""Настройки для сбора и хранения логов (Postgres + ClickHouse)."""

	# RabbitMQ
	RABBITMQ_URL: str = Field(..., alias="RABBITMQ_URL")
	LOGS_EXCHANGE: str = Field("logs", alias="LOGS_EXCHANGE")
	LOG_QUEUE: str = Field("log_queue", alias="LOG_QUEUE")
	LOG_BINDING_KEY: str = Field("log.#", alias="LOG_BINDING_KEY")

	# PostgreSQL History DB
	HISTORY_DATABASE_URL: str = Field(..., alias="HISTORY_DATABASE_URL")

	# ClickHouse (Аналитика) — берем из HistorySettings или напрямую
	CLICKHOUSE_URL: str = Field(..., alias="CLICKHOUSE_URL")
	CLICKHOUSE_HOST: str = Field(..., alias="CLICKHOUSE_HOST")
	CLICKHOUSE_PORT: int = Field(8123, alias="CLICKHOUSE_PORT")
	CLICKHOUSE_USER: str = Field(..., alias="CLICKHOUSE_USER")
	CLICKHOUSE_PASSWORD: str = Field(..., alias="CLICKHOUSE_PASSWORD")
	CLICKHOUSE_DB: str = Field("bank_logs", alias="CLICKHOUSE_DB")
