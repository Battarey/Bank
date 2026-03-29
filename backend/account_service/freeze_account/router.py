"""Роутер для управления блокировками банковских счетов."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared import schemas
from shared.database_core.db import get_session
from shared.internal_auth import require_user_id
from . import service

router = APIRouter(
	prefix="/accounts",
	tags=["accounts"],
)


@router.post(
	"/{account_id}/freeze",
	response_model=schemas.AccountMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Заморозить счёт",
)
async def freeze_account(
	account_id: UUID,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Замораживает банковский счёт текущего пользователя.
	
	Замороженный счёт недоступен для любых расходных операций (переводы, оплата).
	"""
	account = await service.freeze_account(session, user_id, account_id)
	
	return schemas.AccountMessageResponse(
		message="Счёт успешно заморожен.",
		account=schemas.AccountResponse.model_validate(account),
	)


@router.delete(
	"/{account_id}/freeze",
	response_model=schemas.AccountMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Разморозить счёт",
)
async def unfreeze_account(
	account_id: UUID,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Снимает заморозку со счёта, если она была установлена пользователем."""
	account = await service.unfreeze_account(session, user_id, account_id)
	
	return schemas.AccountMessageResponse(
		message="Счёт успешно разморожен.",
		account=schemas.AccountResponse.model_validate(account),
	)
