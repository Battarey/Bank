"""Базовые настройки для всех сервисов системы."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
	"""Абстрактный класс настроек, загружаемых из .env.

	Каждый сервис должен наследовать свой класс Settings от этого класса.
	"""

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",  # Игнорировать лишние поля в .env
	)

	# Окружение: local (dev-машина), test, dev (docker), prod
	APP_ENV: Literal["local", "test", "dev", "prod"] = "local"

	# Общие настройки безопасности (ОБЯЗАТЕЛЬНЫ к заполнению в .env)
	SECRET_KEY: str = Field(..., alias="SECRET_KEY")
	INTERNAL_API_KEY: str = Field(..., alias="INTERNAL_API_KEY")

	@property
	def is_test(self) -> bool:
		"""Проверка, запущены ли тесты."""
		return self.APP_ENV == "test"

	@property
	def is_local(self) -> bool:
		"""Проверка, запущен ли сервис локально (на машине разработчика)."""
		return self.APP_ENV == "local"
