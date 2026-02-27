"""Эндпоинт входа по PIN-коду."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database_core.db import get_session
from shared.schemas.auth import LoginPinRequest, LoginPinResponse
from . import service

router = APIRouter(tags=["auth-login"])


def _raise(exc: service.AuthError) -> None:
	if isinstance(exc, service.AuthNotFound):
		raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
	if isinstance(exc, service.AuthForbidden):
		raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc))
	raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/login-pin", response_model=LoginPinResponse)
async def login_pin(
	body: LoginPinRequest,
	session: AsyncSession = Depends(get_session),
):
	"""Вход по PIN-коду (повторный вход)."""
	try:
		token, user_id = await service.login_pin(session, body.phone, body.pin)
	except service.AuthError as exc:
		_raise(exc)
	return LoginPinResponse(session_token=token, user_id=str(user_id))
