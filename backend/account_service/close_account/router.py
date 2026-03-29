"""Роутер для закрытия банковских счетов."""

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


@router.delete(
	"/{account_id}",
	# response_model=schemas.AccountMessageResponse, # Схемы могут не сойтись, если я меняю тип ответа
	response_model=schemas.AccountMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Закрыть счёт",
)
async def close_account(
	account_id: UUID,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Закрывает банковский счёт текущего пользователя (мягкое удаление).
	
	Счёт не удаляется физически, а переходит в статус 'closed'.
	Для успешного закрытия баланс должен быть нулевым.
	"""
	account = await service.close_account(session, user_id, account_id)
	
	return schemas.AccountMessageResponse(
		message="Счёт успешно закрыт.",
		account=schemas.AccountResponse.model_validate(account),
	)
