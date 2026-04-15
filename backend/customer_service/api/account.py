"""Роутер удаления аккаунта клиента."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared import schemas
from shared.internal_auth import require_user_id

from ..core.uow import CustomerUnitOfWork, get_uow
from ..services import account as service

router = APIRouter(
	prefix="/users",
	tags=["user-account"],
)


@router.delete(
	"/me",
	response_model=schemas.MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Удалить мой аккаунт",
)
async def delete_account(
	user_id: UUID = Depends(require_user_id),
	uow: CustomerUnitOfWork = Depends(get_uow),
):
	"""Выполняет мягкое удаление аккаунта текущего пользователя (мягкое удаление).."""
	await service.delete_account(uow, user_id)
	return schemas.MessageResponse(message="Аккаунт успешно удалён.")
