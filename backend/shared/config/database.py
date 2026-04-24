import logging
from typing import Any

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
	"""Настройки всей инфраструктуры данных: PostgreSQL, Redis.

	Attributes:
		APP_ENV: Текущее окружение (local, test, dev, prod).
		DATABASE_URL: Основной URL для подключения к PostgreSQL через SQLAlchemy.
		TEST_DATABASE_URL: URL для подключения к тестовой базе (используется при APP_ENV=test).
		DB_POOL_SIZE: Размер пула соединений SQLAlchemy.
		DB_MAX_OVERFLOW: Максимальное количество соединений сверх пула.
		DB_POOL_RECYCLE: Время жизни соединения в пуле до сброса.
		REDIS_SESSIONS_URL: URL для подключения к Redis (сессии).
		REDIS_ONBOARDING_URL: URL для подключения к Redis (онбординг).
		REDIS_SESSION_TTL: Время жизни сессии в Redis (в секундах).
	"""

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)

	# Окружение (нужно для валидаторов)
	APP_ENV: str = Field("local", alias="APP_ENV")

	# PostgreSQL Core
	DATABASE_URL: str | None = Field(None, alias="DATABASE_URL")
	TEST_DATABASE_URL: str | None = Field(None, alias="TEST_DATABASE_URL")
	HISTORY_DATABASE_URL: str | None = Field(None, alias="HISTORY_DATABASE_URL")

	DB_POOL_SIZE: int = Field(10, alias="DB_POOL_SIZE")
	DB_MAX_OVERFLOW: int = Field(20, alias="DB_MAX_OVERFLOW")
	DB_POOL_RECYCLE: int = Field(1800, alias="DB_POOL_RECYCLE")

	# Redis (хранение сессий и черновиков онбординга)
	REDIS_SESSIONS_URL: str | None = Field(
		None, validation_alias=AliasChoices("REDIS_SESSIONS_URL", "REDIS_URL", "redis_sessions_url")
	)
	REDIS_ONBOARDING_URL: str | None = Field(
		None, validation_alias=AliasChoices("REDIS_ONBOARDING_URL", "REDIS_URL", "redis_onboarding_url")
	)
	REDIS_SESSION_TTL: int = Field(1800, alias="REDIS_SESSION_TTL")

	@model_validator(mode="before")
	@classmethod
	def use_test_database(cls, data: Any) -> Any:
		"""Автоматически переключает URL на тестовый, если APP_ENV=test."""
		if isinstance(data, dict):
			app_env = data.get("APP_ENV", "local")
			if app_env == "test":
				test_url = data.get("TEST_DATABASE_URL")
				if test_url:
					logger.info("Switching to TEST_DATABASE_URL because APP_ENV=test")
					data["DATABASE_URL"] = test_url
				else:
					logger.warning("APP_ENV=test but TEST_DATABASE_URL is not set!")
		return data


class HistorySettings(BaseSettings):
	"""Настройки для Clickhouse (аналитика) или доп. хранилищ истории.

	Attributes:
		APP_ENV: Текущее окружение.
		HOST: Хост для подключения к ClickHouse.
		PORT: Порт ClickHouse (обычно 8123 для HTTP).
		USER: Пользователь ClickHouse.
		PASSWORD: Пароль пользователя.
		DATABASE: Имя базы данных ClickHouse.
	"""

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)

	APP_ENV: str = Field("local", alias="APP_ENV")

	HOST: str = Field("clickhouse", alias="CLICKHOUSE_HOST")
	PORT: int = Field(8123, alias="CLICKHOUSE_PORT")
	USER: str = Field("default", alias="CLICKHOUSE_USER")
	PASSWORD: str = Field("", alias="CLICKHOUSE_PASSWORD")
	DATABASE: str = Field("default", alias="CLICKHOUSE_DB")


class MongoSettings(BaseSettings):
	"""Настройки MongoDB (motor).

	Attributes:
		APP_ENV: Текущее окружение.
		URL: Строка подключения к MongoDB (включая учетные данные и базу).
	"""

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)

	APP_ENV: str = Field("local", alias="APP_ENV")

	URL: str | None = Field(None, alias="MONGO_URL")
