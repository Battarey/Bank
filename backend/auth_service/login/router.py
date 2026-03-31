"""Роутер аутентификации: вход и управление PIN-кодом."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database_core.db import get_session
from shared.internal_auth import require_user_id
from shared.schemas.auth import LoginPinRequest, LoginPinResponse, MessageResponse, SetPinRequest
from . import service

router = APIRouter(tags=["auth-sessions"])


@router.post(
	"/sessions",
	response_model=LoginPinResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Создать сессию (Вход)",
)
async def login(
	body: LoginPinRequest,
	session: AsyncSession = Depends(get_session),
):
	"""Вход в систему по номеру телефона и PIN-коду."""
	token, user_id = await service.login_pin(session, body.phone, body.pin)
	return LoginPinResponse(session_token=token, user_id=str(user_id))


@router.put(
	"/pins",
	response_model=MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Установить/сменить PIN",
)
async def set_pin(
	body: SetPinRequest,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Устанавливает или обновляет PIN-код текущего пользователя."""
	await service.set_pin(session, user_id, body.pin)
	return MessageResponse(message="PIN-код успешно обновлён.")
