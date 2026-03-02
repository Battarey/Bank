"""Роутер для снятия средств с банковского счёта."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared import schemas
from shared.database_core.db import get_session
from shared.internal_auth import require_user_id
from transaction_service.exceptions import (
	AccountNotFound,
	AccountNotOpen,
	InsufficientFunds,
	TransactionConflict,
	TransactionError,
)
from . import service

router = APIRouter(
	prefix="/accounts",
	tags=["transactions"],
)


# ── Маппинг исключений → HTTP ──────────────────────────────────────────

def _raise(exc: TransactionError) -> None:
	"""Маппинг бизнес-исключений → HTTP-ошибки."""
	if isinstance(exc, AccountNotFound):
		raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
	if isinstance(exc, InsufficientFunds):
		raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
	if isinstance(exc, (AccountNotOpen, TransactionConflict)):
		raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
	raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ── Эндпоинты ──────────────────────────────────────────────────────

@router.post(
	"/{account_id}/withdraw",
	response_model=schemas.TransactionMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Снять со счёта",
)
async def withdraw(
	account_id: UUID,
	payload: schemas.WithdrawalRequest,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Списывает средства с банковского счёта."""

	try:
		tx = await service.withdraw(
			session, user_id, account_id,
			amount=payload.amount,
			description=payload.description,
		)
	except TransactionError as exc:
		_raise(exc)

	return schemas.TransactionMessageResponse(
		message="Средства успешно списаны.",
		transaction=schemas.TransactionResponse.model_validate(tx),
	)
