"""Роутер управления сессиями и блокировки аккаунта."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database_core.db import get_session
from shared.internal_auth import require_user_id
from shared.schemas.auth import MessageResponse
from . import service

router = APIRouter(tags=["auth-sessions"])


@router.delete(
	"/sessions/current",
	response_model=MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Завершить текущую сессию (Logout)",
)
async def logout(
	x_session_token: str = Header(..., alias="X-Session-Token"),
):
	"""Удаляет текущий сессионный токен из Redis."""
	await service.logout(x_session_token)
	return MessageResponse(message="Сеанс успешно завершён.")


@router.delete(
	"/sessions",
	response_model=MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Завершить все сессии пользователя",
)
async def logout_all(
	user_id: UUID = Depends(require_user_id),
):
	"""Отзывает все сессионные токены, выданные данному пользователю."""
	await service.logout_all(user_id)
	return MessageResponse(message="Все активные сессии завершены.")


@router.post(
	"/sessions/me/block",
	response_model=MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Самоблокировка аккаунта",
)
async def self_block(
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Блокирует аккаунт пользователя по его инициативе.
	
	Замораживает счета и завершает все сессии. Восстановление доступа
	возможно только через процедуру разблокировки.
	"""
	await service.self_block(session, user_id)
	return MessageResponse(message="Аккаунт заблокирован. Все сессии завершены.")
