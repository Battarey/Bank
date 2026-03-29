"""Роутер для проведения AML / антифрод-проверок транзакций."""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database_core.db import get_session
from . import service


router = APIRouter(tags=["security"])


# ── Схемы запроса/ответа ───────────────────────────────────────────────

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


# ── Эндпоинты ──────────────────────────────────────────────────────────

@router.post(
	"/check",
	response_model=SecurityCheckResponse,
	status_code=status.HTTP_200_OK,
	summary="Проверить транзакцию",
)
async def check_transaction(
	payload: SecurityCheckRequest,
	session: AsyncSession = Depends(get_session),
):
	"""Проверяет входящую операцию на соответствие набору AML-правил безопасности.
	
	Возвращает `allowed: false` при выявлении хотя бы одного нарушения.
	Используется Transaction Service и Account Service перед завершением финансовых проводок.
	"""
	violations = await service.check_transaction(
		session,
		account_id=payload.account_id,
		tx_type=payload.tx_type,
		amount=payload.amount,
		currency=payload.currency,
	)

	return SecurityCheckResponse(
		allowed=len(violations) == 0,
		violations=[
			ViolationItem(
				rule=v.rule,
				threshold=v.threshold,
				actual=v.actual,
				details=v.details,
			)
			for v in violations
		],
	)
