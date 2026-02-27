"""Эндпоинты управления сессиями и PIN-кодом."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database_core.db import get_session
from shared.internal_auth import require_user_id
from shared.schemas.auth import MessageResponse, SetPinRequest
from . import service

router = APIRouter(tags=["auth-session"])


# ── Обработка ошибок ───────────────────────────────────────────────────

def _raise(exc: service.SessionError) -> None:
	if isinstance(exc, service.SessionNotFound):
		raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
	raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ── Эндпоинты ──────────────────────────────────────────────────────────

@router.post("/set-pin", response_model=MessageResponse, summary="Установить / сменить PIN")
async def set_pin(
	body: SetPinRequest,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Устанавливает или обновляет PIN-код текущего пользователя."""
	try:
		await service.set_pin(session, user_id, body.pin)
	except service.SessionError as exc:
		_raise(exc)
	return MessageResponse(message="PIN-код успешно установлен.")


@router.post("/logout", response_model=MessageResponse, summary="Выход")
async def logout(
	x_session_token: str = Header(..., alias="X-Session-Token"),
):
	"""Завершает текущий сеанс."""
	await service.logout(x_session_token)
	return MessageResponse(message="Сеанс завершён.")


@router.post("/logout-all", response_model=MessageResponse, summary="Выход со всех устройств")
async def logout_all(
	user_id: UUID = Depends(require_user_id),
):
	"""Завершает все сеансы пользователя."""
	await service.logout_all(user_id)
	return MessageResponse(message="Все сеансы завершены.")
