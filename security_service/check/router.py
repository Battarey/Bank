"""Роутер антифрод-проверки: POST /check."""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database_core.db import get_session
from . import service

router = APIRouter(tags=["security"])


# ── Схемы запроса/ответа ───────────────────────────────────────────────

class SecurityCheckRequest(BaseModel):
	"""Запрос на проверку pending-транзакции."""

	account_id: UUID = Field(description="UUID счёта")
	tx_type: str = Field(description="Тип операции: deposit | withdrawal | transfer")
	amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2, description="Сумма")
	currency: str = Field(description="Валюта счёта")

	model_config = ConfigDict(extra="forbid")


class ViolationItem(BaseModel):
	"""Одно сработавшее правило."""

	rule: str = Field(description="Имя правила")
	threshold: str = Field(description="Пороговое значение")
	actual: str = Field(description="Фактическое значение")
	details: dict = Field(description="Подробности")


class SecurityCheckResponse(BaseModel):
	"""Результат проверки."""

	allowed: bool = Field(description="true — операция разрешена, false — заблокирована")
	violations: list[ViolationItem] = Field(default_factory=list, description="Сработавшие правила")


# ── Эндпоинт ──────────────────────────────────────────────────────────

@router.post(
	"/check",
	response_model=SecurityCheckResponse,
	summary="Проверить транзакцию на соответствие AML-правилам",
)
async def check(
	payload: SecurityCheckRequest,
	session: AsyncSession = Depends(get_session),
):
	"""Проверяет pending-операцию по 6 AML-правилам.

	Возвращает `allowed: false` и список нарушений, если хотя бы одно правило сработало.
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
