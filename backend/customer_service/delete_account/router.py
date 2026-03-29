"""Роутер удаления аккаунта клиента."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared import schemas
from shared.database_core.db import get_session
from shared.internal_auth import require_user_id
from . import service

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
	session: AsyncSession = Depends(get_session),
):
	"""Выполняет мягкое удаление аккаунта текущего пользователя (мягкое удаление)."""
	await service.delete_account(session, user_id)
	return schemas.MessageResponse(message="Аккаунт успешно удалён.")
