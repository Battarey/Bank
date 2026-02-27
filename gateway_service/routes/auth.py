"""Маршруты auth_service — аутентификация через gateway."""

from fastapi import APIRouter, Depends, Request, status
from shared import schemas
from ..helpers import forward_request
from ..middleware import session_token_scheme

public_router = APIRouter(prefix="/auth", tags=["auth"])
protected_router = APIRouter(
	prefix="/auth",
	tags=["auth"],
	dependencies=[Depends(session_token_scheme)],
)


# ── Публичные ──────────────────────────────────────────────────────────

@public_router.post(
	"/login-pin",
	response_model=schemas.LoginPinResponse,
	status_code=status.HTTP_200_OK,
	summary="Вход по PIN-коду",
)
async def login_pin(payload: schemas.LoginPinRequest, request: Request):
	"""Аутентификация по номеру телефона и PIN-коду. Возвращает сессионный токен."""
	data = await forward_request(
		request,
		"POST",
		"/login-pin",
		payload.model_dump(mode="json"),
		service="auth",
	)
	return schemas.LoginPinResponse.model_validate(data)


# ── Защищённые ─────────────────────────────────────────────────────────

@protected_router.post(
	"/set-pin",
	response_model=schemas.MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Установить / сменить PIN",
)
async def set_pin(payload: schemas.SetPinRequest, request: Request):
	"""Устанавливает или обновляет PIN-код текущего пользователя."""
	data = await forward_request(
		request,
		"POST",
		"/set-pin",
		payload.model_dump(mode="json"),
		service="auth",
	)
	return schemas.MessageResponse.model_validate(data)


@protected_router.post(
	"/logout",
	response_model=schemas.MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Выход",
)
async def logout(request: Request):
	"""Завершает текущий сеанс (удаляет сессионный токен)."""
	data = await forward_request(
		request,
		"POST",
		"/logout",
		service="auth",
	)
	return schemas.MessageResponse.model_validate(data)


@protected_router.post(
	"/logout-all",
	response_model=schemas.MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Выход со всех устройств",
)
async def logout_all(request: Request):
	"""Завершает все активные сеансы пользователя."""
	data = await forward_request(
		request,
		"POST",
		"/logout-all",
		service="auth",
	)
	return schemas.MessageResponse.model_validate(data)
