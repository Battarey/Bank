"""Роутер для открытия, просмотра и получения банковских счетов."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared import schemas
from shared.database_core.db import get_session
from shared.internal_auth import require_user_id
from account_service.exceptions import (
	AccountConflict,
	AccountError,
	AccountLimitReached,
	AccountNotFound,
	AccountOwnerNotFound,
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
	if isinstance(exc, AccountOwnerNotFound):
		raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
	if isinstance(exc, (AccountLimitReached, AccountConflict)):
		raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
	raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ── Эндпоинты ──────────────────────────────────────────────────────────

@router.post(
	"",
	response_model=schemas.AccountMessageResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Открыть новый счёт",
)
async def open_account(
	payload: schemas.OpenAccountRequest,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Создаёт банковский счёт указанного типа и валюты."""

	try:
		account = await service.open_account(session, user_id, payload)
	except AccountError as exc:
		_raise(exc)

	return schemas.AccountMessageResponse(
		message="Счёт успешно открыт.",
		account=schemas.AccountResponse.model_validate(account),
	)


@router.get(
	"",
	response_model=schemas.AccountListResponse,
	status_code=status.HTTP_200_OK,
	summary="Список счетов пользователя",
)
async def list_accounts(
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Возвращает все счета текущего пользователя."""

	accounts = await service.list_accounts(session, user_id)
	return schemas.AccountListResponse(
		accounts=[schemas.AccountResponse.model_validate(a) for a in accounts],
		total=len(accounts),
	)


@router.get(
	"/{account_id}",
	response_model=schemas.AccountResponse,
	status_code=status.HTTP_200_OK,
	summary="Детали счёта",
)
async def get_account(
	account_id: UUID,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Возвращает данные конкретного счёта, если он принадлежит пользователю."""

	try:
		account = await service.get_account(session, user_id, account_id)
	except AccountError as exc:
		_raise(exc)

	return schemas.AccountResponse.model_validate(account)
