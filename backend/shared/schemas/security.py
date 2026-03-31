"""Pydantic-схемы для сервиса безопасности (AML/Antifraud)."""

from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class SecurityCheckRequest(BaseModel):
	"""Запрос на проверку транзакции перед её выполнением."""

	account_id: UUID = Field(description="Уникальный идентификатор счёта")
	tx_type: str = Field(description="Тип операции (deposit, withdrawal, transfer)")
	amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2, description="Сумма операции")
	currency: str = Field(description="Код валюты (RUB, USD, EUR)")

	model_config = ConfigDict(extra="forbid")


class ViolationItem(BaseModel):
	"""Описание одного зафиксированного нарушения AML-правил."""

	rule: str = Field(description="Название сработавшего правила")
	threshold: str = Field(description="Пороговое значение правила")
	actual: str = Field(description="Фактическое значение в транзакции")
	details: dict = Field(description="Технические подробности для администратора")


class SecurityCheckResponse(BaseModel):
	"""Результат AML-проверки транзакции."""

	allowed: bool = Field(description="Разрешить операцию (true) или заблокировать (false)")
	violations: list[ViolationItem] = Field(default_factory=list, description="Список нарушений")
