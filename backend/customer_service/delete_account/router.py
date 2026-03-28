"""Роутер удаления аккаунта клиента."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
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
	"/delete",
	response_model=schemas.MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Удалить аккаунт",
)
async def delete_account(
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Soft delete аккаунта: статус → deleted, счета заморожены, сессии отозваны."""

	try:
		await service.delete_account(session, user_id)
	except service.DeleteAccountNotFound as exc:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=str(exc),
		) from exc
	except service.DeleteAccountAlreadyDeleted as exc:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail=str(exc),
		) from exc

	return schemas.MessageResponse(message="Аккаунт успешно удалён.")
