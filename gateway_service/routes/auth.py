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
)
async def login_pin(payload: schemas.LoginPinRequest, request: Request):
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
)
async def set_pin(payload: schemas.SetPinRequest, request: Request):
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
)
async def logout(request: Request):
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
)
async def logout_all(request: Request):
	data = await forward_request(
		request,
		"POST",
		"/logout-all",
		service="auth",
	)
	return schemas.MessageResponse.model_validate(data)
