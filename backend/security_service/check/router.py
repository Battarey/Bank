"""Роутер для проведения AML / антифрод-проверок транзакций."""

from fastapi import APIRouter, Depends, status

from shared.schemas import (
	SecurityCheckRequest,
	SecurityCheckResponse,
	ViolationItem,
)

from ..mongo_repository import SecurityEventRepository, get_mongo_repo
from ..uow import SecurityUnitOfWork, get_uow
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
	uow: SecurityUnitOfWork = Depends(get_uow),
	mongo_repo: SecurityEventRepository = Depends(get_mongo_repo),
):
	"""Проверяет входящую операцию на соответствие набору AML-правил безопасности.

	Используется Transaction Service и Account Service перед завершением финансовых проводок.
	Возвращает `allowed: false` при выявлении хотя бы одного нарушения.

	Args:
		payload: Данные транзакции (счёт, тип, сумма, валюта).
		uow: Unit of Work для управления транзакцией и событиями.
		mongo_repo: Репозиторий событий безопасности (MongoDB).

	Returns:
		SecurityCheckResponse: Результат проверки со списком нарушений.
	"""
	violations = await service.check_transaction(
		uow,
		mongo_repo=mongo_repo,
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
