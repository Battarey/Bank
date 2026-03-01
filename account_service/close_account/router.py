"""Роутер для закрытия банковского счёта."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared import schemas
from shared.database_core.db import get_session
from shared.internal_auth import require_user_id
from account_service.exceptions import (
	AccountConflict,
	AccountError,
	AccountNonZeroBalance,
	AccountNotFound,
	AccountNotOpen,
)
from . import service

router = APIRouter(
	prefix="/accounts",
	tags=["accounts"],
)


# ── Маппинг исключений → HTTP ──────────────────────────────────────────

def _raise(exc: AccountError) -> None:
	"""Единообразное преобразование бизнес-исключений в HTTP-ошибки."""
	if isinstance(exc, AccountNotFound):
		raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
	if isinstance(exc, (AccountNotOpen, AccountNonZeroBalance, AccountConflict)):
		raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
	raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ── Эндпоинты ──────────────────────────────────────────────────────────

@router.post(
	"/{account_id}/close",
	response_model=schemas.AccountMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Закрыть счёт",
)
async def close_account(
	account_id: UUID,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Закрывает банковский счёт. Баланс должен быть 0."""

	try:
		account = await service.close_account(session, user_id, account_id)
	except AccountError as exc:
		_raise(exc)

	return schemas.AccountMessageResponse(
		message="Счёт успешно закрыт.",
		account=schemas.AccountResponse.model_validate(account),
	)
