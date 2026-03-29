"""Роутер для снятия средств с банковских счетов."""

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
	"/{account_id}/withdrawal",
	response_model=schemas.TransactionMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Снять средства",
)
async def withdraw(
	account_id: UUID,
	payload: schemas.WithdrawRequest,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Выполняет снятие (списание) средств с указанного счёта.
	
	Включает антифрод-проверку. Операция доступна только владельцу активного счёта.
	"""
	tx = await service.withdraw(
		session, 
		user_id,
		account_id=account_id,
		amount=payload.amount,
		description=payload.description,
	)
	
	return schemas.TransactionMessageResponse(
		message="Снятие успешно выполнено.",
		transaction=schemas.TransactionResponse.model_validate(tx),
	)
