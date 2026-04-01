"""Auth Service — аутентификация: PIN + сессии + разблокировка."""

from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI

from shared.config import BaseAppSettings
from shared.bootstrap import bootstrap, get_container

# Инициализация инфраструктуры
bootstrap(BaseAppSettings)
container = get_container()

from shared.internal_auth import verify_internal_key
from shared.rabbitmq.client import connect as rmq_connect, disconnect as rmq_disconnect
from shared.redis_sessions import client as redis_client
from shared.utils.exceptions_handler import setup_exception_handlers

from .login.router import router as login_router
from .session.router import router as session_router
from .unlock.router import router as unlock_router


@asynccontextmanager
async def lifespan(app: FastAPI):
	await rmq_connect()
	yield
	await rmq_disconnect()
	await redis_client.close_client()
	await container.dispose()


app = FastAPI(
	title="Auth Service",
	version="0.3.0",
	description="Сервис управления доступом: вход по PIN, сессии, блокировка и разблокировка.",
	lifespan=lifespan,
	dependencies=[Depends(verify_internal_key)],
	openapi_tags=[
		{
			"name": "auth-sessions",
			"description": "Управление входом и активными сеансами пользователя.",
		},
		{
			"name": "auth-unlock",
			"description": "Восстановление доступа к заблокированному аккаунту.",
		},
		{
			"name": "health",
			"description": "Проверка работоспособности сервиса.",
		},
	],
)

# Регистрация глобального обработчика ошибок BaseBusinessError
setup_exception_handlers(app)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
	return {"status": "ok"}


app.include_router(login_router)
app.include_router(session_router)
app.include_router(unlock_router)
