"""Базовые настройки для всех сервисов системы."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .database import DatabaseSettings, HistorySettings, MongoSettings
from .rabbitmq import RabbitMQSettings


class BaseAppSettings(BaseSettings):
	"""Абстрактный класс настроек, загружаемых из .env.

	Каждый сервис должен наследовать свой класс Settings от этого класса.

	Attributes:
		APP_ENV: Текущее окружение (local, test, dev, prod).
		SECRET_KEY: Секретный ключ приложения для JWT и безопасности.
		INTERNAL_API_KEY: Ключ для аутентификации внутренних межсервисных запросов.
		ENCRYPTION_KEY: Ключ для симметричного шифрования чувствительных данных.
		BLIND_INDEX_SALT: Соль для создания детерминированных поисковых индексов.
		db: Настройки основной базы данных и Redis.
		rabbitmq: Настройки брокера сообщений RabbitMQ.
		history: Настройки аналитической базы ClickHouse.
		mongo: Настройки документоориентированной базы MongoDB.
	"""

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",  # Игнорировать лишние поля в .env
	)

	# Окружение: local (dev-машина), test, dev (docker), prod
	APP_ENV: Literal["local", "test", "dev", "prod"] = "local"

	# Общие настройки безопасности (ОБЯЗАТЕЛЬНЫ к заполнению в .env основных сервисов)
	SECRET_KEY: str | None = Field(None, alias="SECRET_KEY")
	INTERNAL_API_KEY: str | None = Field(None, alias="INTERNAL_API_KEY")
	ENCRYPTION_KEY: str | None = Field(None, alias="ENCRYPTION_KEY")
	BLIND_INDEX_SALT: str = Field("bank_default_salt_2024", alias="BLIND_INDEX_SALT")

	# Вложенные настройки (Composition)
	db: DatabaseSettings = Field(default_factory=DatabaseSettings)
	rabbitmq: RabbitMQSettings = Field(default_factory=RabbitMQSettings)
	history: HistorySettings = Field(default_factory=HistorySettings)
	mongo: MongoSettings = Field(default_factory=MongoSettings)

	@property
	def is_test(self) -> bool:
		"""Проверка, запущены ли тесты."""
		return self.APP_ENV == "test"

	@property
	def is_local(self) -> bool:
		"""Проверка, запущен ли сервис локально (на машине разработчика)."""
		return self.APP_ENV == "local"
