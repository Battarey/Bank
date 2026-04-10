import logging
import os

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
	"""Настройки всей инфраструктуры данных: PostgreSQL, Redis."""

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)

	# PostgreSQL Core
	DATABASE_URL: str = Field(..., alias="DATABASE_URL")
	TEST_DATABASE_URL: str | None = Field(None, alias="TEST_DATABASE_URL")

	DB_POOL_SIZE: int = Field(10, alias="DB_POOL_SIZE")
	DB_MAX_OVERFLOW: int = Field(20, alias="DB_MAX_OVERFLOW")
	DB_POOL_RECYCLE: int = Field(1800, alias="DB_POOL_RECYCLE")

	# Redis (хранение сессий и черновиков онбординга)
	REDIS_SESSIONS_URL: str | None = Field(
		None, 
		validation_alias=AliasChoices("REDIS_SESSIONS_URL", "REDIS_URL", "redis_sessions_url")
	)
	REDIS_ONBOARDING_URL: str | None = Field(
		None, 
		validation_alias=AliasChoices("REDIS_ONBOARDING_URL", "REDIS_URL", "redis_onboarding_url")
	)
	REDIS_SESSION_TTL: int = Field(1800, alias="REDIS_SESSION_TTL")

	@model_validator(mode='after')
	def use_test_database(self) -> 'DatabaseSettings':
		"""Автоматически переключает URL на тестовый, если APP_ENV=test."""
		if os.getenv("APP_ENV") == "test":
			if self.TEST_DATABASE_URL:
				logger.info("Switching to TEST_DATABASE_URL because APP_ENV=test")
				self.DATABASE_URL = self.TEST_DATABASE_URL
			else:
				logger.warning("APP_ENV=test but TEST_DATABASE_URL is not set!")
		return self
	

class HistorySettings(BaseSettings):
	"""Настройки для Clickhouse (аналитика) или доп. хранилищ истории."""

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)

	CLICKHOUSE_URL: str = Field(..., alias="CLICKHOUSE_URL")
