"""Роутер для проведения межбанковских и внутренних переводов."""

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
	"/{account_id}/transfer",
	response_model=schemas.TransactionMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Выполнить перевод",
)
async def transfer(
	account_id: UUID,
	payload: schemas.TransferRequest,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Переводит средства с указанного счёта на другой счёт внутри банка.
	
	Поддерживает конвертацию валют и AML-проверку. 
	В случае подозрительной операции счёт может быть автоматически заморожен.
	"""
	tx = await service.transfer(
		session, 
		user_id,
		from_account_id=account_id,
		to_account_id=payload.to_account_id,
		amount=payload.amount,
		description=payload.description,
	)
	
	return schemas.TransactionMessageResponse(
		message="Перевод успешно выполнен.",
		transaction=schemas.TransactionResponse.model_validate(tx),
	)
