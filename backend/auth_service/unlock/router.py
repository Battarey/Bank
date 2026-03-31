"""Роутер разблокировки аккаунта: запрос кода и подтверждение."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database_core.db import get_session
from shared.schemas.auth import MessageResponse
from shared.schemas.unlock import RequestUnlockRequest, UnlockRequest
from . import service

router = APIRouter(tags=["auth-unlock"])


@router.post(
	"/unlock-codes",
	response_model=MessageResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Запросить код разблокировки",
)
async def request_unlock(
	body: RequestUnlockRequest,
	session: AsyncSession = Depends(get_session),
):
	"""Генерирует 6-значный код и отправляет его на Email пользователя."""
	await service.request_unlock(session, body.email)
	return MessageResponse(message="Код разблокировки отправлен на привязанный Email.")


@router.post(
	"/unlock-codes/verifications",
	response_model=MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Подтвердить разблокировку",
)
async def confirm_unlock(
	body: UnlockRequest,
	session: AsyncSession = Depends(get_session),
):
	"""Проверяет код и переводит аккаунт в статус 'active'."""
	await service.confirm_unlock(session, body.email, body.code)
	return MessageResponse(message="Аккаунт успешно разблокирован. Теперь вы можете войти.")
