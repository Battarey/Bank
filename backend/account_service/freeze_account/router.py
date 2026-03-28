"""Роутер заморозки / разморозки банковского счёта."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared import schemas
from shared.database_core.db import get_session
from shared.internal_auth import require_user_id
from account_service.exceptions import (
	AccountAlreadyFrozen,
	AccountError,
	AccountNotFound,
	AccountNotFrozen,
	AccountNotOpen,
	UnfreezeNotAllowed,
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
	if isinstance(exc, AccountAlreadyFrozen):
		raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
	if isinstance(exc, AccountNotFrozen):
		raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
	if isinstance(exc, UnfreezeNotAllowed):
		raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc))
	if isinstance(exc, AccountNotOpen):
		raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
	raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ── Эндпоинты ──────────────────────────────────────────────────────────

@router.post(
	"/{account_id}/freeze",
	response_model=schemas.AccountMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Заморозить счёт",
)
async def freeze(
	account_id: UUID,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Замораживает банковский счёт по запросу владельца."""

	try:
		account = await service.freeze_account(session, user_id, account_id)
	except AccountError as exc:
		_raise(exc)

	return schemas.AccountMessageResponse(
		message="Счёт заморожен.",
		account=schemas.AccountResponse.model_validate(account),
	)


@router.post(
	"/{account_id}/unfreeze",
	response_model=schemas.AccountMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Разморозить счёт",
)
async def unfreeze(
	account_id: UUID,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Размораживает счёт. Доступно только если заморозка была инициирована пользователем."""

	try:
		account = await service.unfreeze_account(session, user_id, account_id)
	except AccountError as exc:
		_raise(exc)

	return schemas.AccountMessageResponse(
		message="Счёт разморожен.",
		account=schemas.AccountResponse.model_validate(account),
	)
