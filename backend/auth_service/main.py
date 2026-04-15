"""Auth Service — аутентификация: PIN + сессии + разблокировка."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from shared.bootstrap import bootstrap, get_container
from shared.config import BaseAppSettings

# Инициализация инфраструктуры
bootstrap(BaseAppSettings)
container = get_container()

from shared.internal_auth import verify_internal_key
from shared.rabbitmq.client import connect as rmq_connect
from shared.rabbitmq.client import disconnect as rmq_disconnect
from shared.redis_sessions import client as redis_client
from shared.utils.exceptions_handler import setup_exception_handlers

from .api.login import router as login_router
from .api.session import router as session_router
from .api.unlock import router as unlock_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
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
async def health_check() -> dict:
	"""Глубокая проверка работоспособности сервиса и его зависимостей."""
	from shared.database_core.db import ping_db
	from shared.rabbitmq.client import ping_rabbitmq

	db_ok = await ping_db()
	redis_ok = await redis_client.ping()
	rmq_ok = await ping_rabbitmq()

	overall_status = "ok" if db_ok and redis_ok and rmq_ok else "error"
	
	return {
		"status": overall_status,
		"dependencies": {
			"postgres": "ok" if db_ok else "error",
			"redis_sessions": "ok" if redis_ok else "error",
			"rabbitmq": "ok" if rmq_ok else "error",
		},
	}


app.include_router(login_router)
app.include_router(session_router)
app.include_router(unlock_router)
