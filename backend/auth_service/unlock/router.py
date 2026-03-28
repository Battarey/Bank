"""Эндпоинты разблокировки аккаунта."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database_core.db import get_session
from shared.schemas.unlock import RequestUnlockRequest, UnlockRequest
from shared.schemas.auth import MessageResponse
from . import service

router = APIRouter(tags=["auth-unlock"])


def _raise(exc: service.UnlockError) -> None:
	if isinstance(exc, service.UnlockNotFound):
		raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
	if isinstance(exc, service.UnlockNotBlocked):
		raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
	if isinstance(exc, service.UnlockInvalidCode):
		raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))
	raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
	"/request-unlock",
	response_model=MessageResponse,
	summary="Запросить код разблокировки",
)
async def request_unlock(
	body: RequestUnlockRequest,
	session: AsyncSession = Depends(get_session),
):
	"""Отправляет 6-значный код на email для разблокировки аккаунта."""
	try:
		await service.request_unlock(session, body.email)
	except service.UnlockError as exc:
		_raise(exc)
	return MessageResponse(message="Код разблокировки отправлен на привязанный email.")


@router.post(
	"/unlock",
	response_model=MessageResponse,
	summary="Разблокировать аккаунт",
)
async def unlock(
	body: UnlockRequest,
	session: AsyncSession = Depends(get_session),
):
	"""Проверяет код и разблокирует аккаунт."""
	try:
		await service.unlock_account(session, body.email, body.code)
	except service.UnlockError as exc:
		_raise(exc)
	return MessageResponse(message="Аккаунт успешно разблокирован. Теперь вы можете войти по PIN-коду.")
