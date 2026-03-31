"""Роутер разблокировки аккаунта: запрос кода и подтверждение."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.schemas import MessageResponse, RequestUnlockRequest, UnlockRequest
from ..uow import AuthUnitOfWork, get_uow
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
	uow: AuthUnitOfWork = Depends(get_uow),
):
	"""Генерирует 6-значный код и отправляет его на Email пользователя.

	Args:
		body: Email пользователя для поиска аккаунта.
		uow: Unit of Work для управления транзакцией и событиями.

	Returns:
		MessageResponse: Подтверждение отправки кода.
	"""
	await service.request_unlock(uow, body.email)
	return MessageResponse(message="Код разблокировки отправлен на привязанный Email.")


@router.post(
	"/unlock-codes/verifications",
	response_model=MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Подтвердить разблокировку",
)
async def confirm_unlock(
	body: UnlockRequest,
	uow: AuthUnitOfWork = Depends(get_uow),
):
	"""Проверяет код и переводит аккаунт в статус 'active'.

	Args:
		body: Email пользователя и 6-значный код из письма.
		uow: Unit of Work для управления транзакцией и событиями.

	Returns:
		MessageResponse: Подтверждение успешной разблокировки.
	"""
	await service.confirm_unlock(uow, body.email, body.code)
	return MessageResponse(message="Аккаунт успешно разблокирован. Теперь вы можете войти.")
