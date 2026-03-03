"""Роутер для переводов между счетами."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared import schemas
from shared.database_core.db import get_session
from shared.internal_auth import require_user_id
from transaction_service.exceptions import (
	AccountFrozen,
	AccountNotFound,
	AccountNotOpen,
	CurrencyMismatch,
	InsufficientFunds,
	SameAccountTransfer,
	SecurityViolation,
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
	if isinstance(exc, (AccountFrozen, SecurityViolation)):
		raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc))
	if isinstance(exc, InsufficientFunds):
		raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
	if isinstance(exc, CurrencyMismatch):
		raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
	if isinstance(exc, (AccountNotOpen, SameAccountTransfer, TransactionConflict)):
		raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
	raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ── Эндпоинты ──────────────────────────────────────────────────────

@router.post(
	"/{account_id}/transfer",
	response_model=schemas.TransactionMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Перевести на другой счёт",
)
async def transfer(
	account_id: UUID,
	payload: schemas.TransferRequest,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Переводит средства на другой счёт (свой или чужой внутри банка)."""

	try:
		tx = await service.transfer(
			session, user_id,
			from_account_id=account_id,
			to_account_id=payload.to_account_id,
			amount=payload.amount,
			description=payload.description,
		)
	except TransactionError as exc:
		_raise(exc)

	return schemas.TransactionMessageResponse(
		message="Перевод выполнен.",
		transaction=schemas.TransactionResponse.model_validate(tx),
	)
