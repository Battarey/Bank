"""Маршруты auth_service — аутентификация через gateway."""

from fastapi import APIRouter, Depends, Request, status
from shared import schemas
from shared.schemas.unlock import RequestUnlockRequest, UnlockRequest
from shared.redis_sessions.tokens import update_token_data
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


@public_router.post(
	"/request-unlock",
	response_model=schemas.MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Запросить код разблокировки",
)
async def request_unlock(payload: RequestUnlockRequest, request: Request):
	"""Отправляет код разблокировки на email привязанный к аккаунту."""
	data = await forward_request(
		request,
		"POST",
		"/request-unlock",
		payload.model_dump(mode="json"),
		service="auth",
	)
	return schemas.MessageResponse.model_validate(data)


@public_router.post(
	"/unlock",
	response_model=schemas.MessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Разблокировать аккаунт",
)
async def unlock(payload: UnlockRequest, request: Request):
	"""Проверяет код и разблокирует аккаунт."""
	data = await forward_request(
		request,
		"POST",
		"/unlock",
		payload.model_dump(mode="json"),
		service="auth",
	)
	return schemas.MessageResponse.model_validate(data)


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

	# Обновляем сессию: PIN теперь установлен
	token = request.headers.get("X-Session-Token")
	if token:
		await update_token_data(token, {"has_pin": "true"})

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
