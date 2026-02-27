"""Auth Service — аутентификация: PIN + сессии."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from shared.internal_auth import verify_internal_key
from shared.redis_sessions import client as redis_client

from .login.router import router as login_router
from .session.router import router as session_router


@asynccontextmanager
async def lifespan(app: FastAPI):
	yield
	await redis_client.close_client()


app = FastAPI(
	title="Auth Service",
	version="0.1.0",
	description="Внутренний сервис аутентификации: вход по PIN, установка PIN, управление сессиями.",
	lifespan=lifespan,
	dependencies=[Depends(verify_internal_key)],
	openapi_tags=[
		{
			"name": "auth-login",
			"description": "Вход по PIN-коду.",
		},
		{
			"name": "auth-session",
			"description": "Установка PIN, выход из сессии, выход со всех устройств.",
		},
		{
			"name": "health",
			"description": "Проверка работоспособности сервиса.",
		},
	],
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
	return {"status": "ok"}


app.include_router(login_router)
app.include_router(session_router)
