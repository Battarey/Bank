"""Роутер для закрытия банковских счетов."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared import schemas
from shared.internal_auth import require_user_id

from ..uow import AccountUnitOfWork, get_uow
from . import service

router = APIRouter(
	prefix="/accounts",
	tags=["accounts"],
)


@router.delete(
	"/{account_id}",
	response_model=schemas.AccountMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Закрыть счёт",
)
async def close_account(
	account_id: UUID,
	user_id: UUID = Depends(require_user_id),
	uow: AccountUnitOfWork = Depends(get_uow),
):
	"""Закрывает банковский счёт текущего пользователя (мягкое удаление).

	Счёт не удаляется физически, а переходит в статус 'closed'.
	Для успешного закрытия баланс должен быть нулевым.
	"""
	account = await service.close_account(uow, user_id, account_id)

	return schemas.AccountMessageResponse(
		message="Счёт успешно закрыт.",
		account=schemas.AccountResponse.model_validate(account),
	)
