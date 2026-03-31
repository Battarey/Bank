"""Роутер для проведения AML / антифрод-проверок транзакций."""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database_core.db import get_session
from shared.schemas.security import SecurityCheckRequest, SecurityCheckResponse, ViolationItem
from . import service


# ── Эндпоинты ──────────────────────────────────────────────────────────

router = APIRouter(prefix="/security", tags=["Security"])

@router.post(
	"/evaluations",
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
