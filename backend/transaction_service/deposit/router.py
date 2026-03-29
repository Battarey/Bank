"""Роутер для пополнения банковских счетов."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared import schemas
from shared.database_core.db import get_session
from shared.internal_auth import require_user_id
from . import service

router = APIRouter(
	prefix="/accounts",
	tags=["transactions"],
)


@router.post(
	"/{account_id}/deposit",
	# response_model=schemas.TransactionMessageResponse,
	response_model=schemas.TransactionMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Пополнить счёт",
)
async def deposit(
	account_id: UUID,
	payload: schemas.DepositRequest,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Пополняет баланс указанного счёта.
	
	Операция доступна владельцу счёта. Пополнение разрешено даже если счёт заморожен.
	"""
	tx = await service.deposit(
		session, 
		user_id,
		account_id=account_id,
		amount=payload.amount,
		description=payload.description,
	)
	
	return schemas.TransactionMessageResponse(
		message="Пополнение успешно выполнено.",
		transaction=schemas.TransactionResponse.model_validate(tx),
	)
