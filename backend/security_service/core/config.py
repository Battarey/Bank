"""Security Settings.

Централизованная конфигурация для Security Service, включающая настройки
баз данных и константы для AML-мониторинга.
"""

from decimal import Decimal
from pydantic import Field

from shared.config import BaseAppSettings


class SecuritySettings(BaseAppSettings):
	"""Настройки для антифрод-мониторинга (SQL + MongoDB + RabbitMQ).

	Attributes:
		SECURITY_COLLECTION: Название коллекции для логов безопасности.
		SECURITY_TTL_DAYS: Срок хранения логов в днях.
		LARGE_TX_THRESHOLD: Порог крупной разовой операции.
		DAILY_AMOUNT_LIMIT: Дневной лимит суммы исходящих операций.
		DAILY_TX_COUNT: Дневной лимит количества операций.
		RAPID_FIRE_COUNT: Порог срабатывания правила частых операций.
		RAPID_FIRE_WINDOW_MIN: Окно в минутах для частых операций.
		STRUCTURING_RATIO: Коэффициент близости к лимиту для правила структурирования.
		STRUCTURING_MIN_HITS: Минимальное количество попаданий для правила структурирования.
		ROUND_AMOUNT_FLOOR: Минимальная сумма для проверки правила круглых сумм.
		ROUND_AMOUNT_STEP: Шаг округления для правила круглых сумм.
		ROUND_AMOUNT_MIN_HITS: Минимальное количество попаданий для правила круглых сумм.
	"""

	# Константы коллекции (специфично для Security Service)
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
