"""Настройки Security Service."""

from pydantic import Field

from shared.config import BaseAppSettings


class SecuritySettings(BaseAppSettings):
	"""Настройки для антифрод-мониторинга (SQL + MongoDB + RabbitMQ)."""

	# MongoDB (Журнал событий безопасности)
	MONGO_URL: str = Field(
		"mongodb://mongodb:27017/bank_security_db", 
		alias="MONGO_URL"
	)
	
	# Константы коллекции
	SECURITY_COLLECTION: str = Field("security_events", alias="SECURITY_COLLECTION")
	SECURITY_TTL_DAYS: int = Field(365, alias="SECURITY_TTL_DAYS")
