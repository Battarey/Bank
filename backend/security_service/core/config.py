"""Настройки Security Service."""

from decimal import Decimal
from pydantic import Field

from shared.config import BaseAppSettings


class SecuritySettings(BaseAppSettings):
	"""Настройки для антифрод-мониторинга (SQL + MongoDB + RabbitMQ)."""

	# MongoDB (Журнал событий безопасности)
	MONGO_URL: str = Field("mongodb://mongodb:27017/bank_security_db", alias="MONGO_URL")

	# Константы коллекции
	SECURITY_COLLECTION: str = Field("security_events", alias="SECURITY_COLLECTION")
	SECURITY_TTL_DAYS: int = Field(365, alias="SECURITY_TTL_DAYS")

	# Настройки AML-правил
	LARGE_TX_THRESHOLD: Decimal = Field(Decimal("600000"), alias="LARGE_TX_THRESHOLD")
	DAILY_AMOUNT_LIMIT: Decimal = Field(Decimal("1000000"), alias="DAILY_AMOUNT_LIMIT")
	DAILY_TX_COUNT: int = Field(20, alias="DAILY_TX_COUNT")
	RAPID_FIRE_COUNT: int = Field(5, alias="RAPID_FIRE_COUNT")
	RAPID_FIRE_WINDOW_MIN: int = Field(3, alias="RAPID_FIRE_WINDOW_MIN")
	STRUCTURING_RATIO: Decimal = Field(Decimal("0.9"), alias="STRUCTURING_RATIO")
	STRUCTURING_MIN_HITS: int = Field(3, alias="STRUCTURING_MIN_HITS")
	ROUND_AMOUNT_FLOOR: Decimal = Field(Decimal("100000"), alias="ROUND_AMOUNT_FLOOR")
	ROUND_AMOUNT_STEP: Decimal = Field(Decimal("10000"), alias="ROUND_AMOUNT_STEP")
	ROUND_AMOUNT_MIN_HITS: int = Field(3, alias="ROUND_AMOUNT_MIN_HITS")
