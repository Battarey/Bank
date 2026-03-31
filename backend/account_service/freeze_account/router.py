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
	"/{account_id}/suspensions",
	response_model=schemas.AccountMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Приостановить обслуживание счёта",
)
async def suspend_account(
	account_id: UUID,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Приостанавливает операции по банковскому счёту (заморозка).
	
	Замороженный счёт недоступен для любых расходных операций (переводы, оплата).
	"""
	account = await service.freeze_account(session, user_id, account_id)
	
	return schemas.AccountMessageResponse(
		message="Обслуживание счёта приостановлено.",
		account=schemas.AccountResponse.model_validate(account),
	)


@router.delete(
	"/{account_id}/suspensions",
	response_model=schemas.AccountMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Возобновить обслуживание счёта",
)
async def resume_account(
	account_id: UUID,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Снимает приостановку со счёта (разморозка), если она была установлена пользователем."""
	account = await service.unfreeze_account(session, user_id, account_id)
	
	return schemas.AccountMessageResponse(
		message="Обслуживание счёта возобновлено.",
		account=schemas.AccountResponse.model_validate(account),
	)
