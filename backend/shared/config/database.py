"""Настройки подключения к базам данных."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
	"""Настройки PostgreSQL."""

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)

	# PostgreSQL Core
	DATABASE_URL: str = Field(..., alias="DATABASE_URL")
	DB_POOL_SIZE: int = Field(10, alias="DB_POOL_SIZE")
	DB_MAX_OVERFLOW: int = Field(20, alias="DB_MAX_OVERFLOW")
	DB_POOL_RECYCLE: int = Field(1800, alias="DB_POOL_RECYCLE")


class RedisSettings(BaseSettings):
	"""Настройки Redis для разных целей."""

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)

	REDIS_URL: str = Field(..., alias="REDIS_URL")
	SESSION_TTL: int = Field(1800, alias="REDIS_SESSION_TTL")


class HistorySettings(BaseSettings):
	"""Настройки для Clickhouse (аналитика) или доп. хранилищ истории."""

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)

	CLICKHOUSE_URL: str = Field(..., alias="CLICKHOUSE_URL")
