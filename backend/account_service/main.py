"""Account Service — управление банковскими счетами: открытие, просмотр, блокировка и закрытие."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from shared.bootstrap import bootstrap, get_container
from shared.config import BaseAppSettings

# Инициализация инфраструктуры (Settings, DB Engine, Session Factory)
bootstrap(BaseAppSettings)
container = get_container()

from shared.internal_auth import verify_internal_key
from shared.rabbitmq.client import connect as rmq_connect
from shared.rabbitmq.client import disconnect as rmq_disconnect
from shared.utils.exceptions_handler import setup_exception_handlers

from .api.accounts import router as accounts_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
	await rmq_connect()
	yield
	await rmq_disconnect()
	await container.dispose()


app = FastAPI(
	title="Account Service",
	version="0.3.0",
	description="Сервис управления жизненным циклом банковских счетов: открытие, мониторинг, блокировка и закрытие.",
	lifespan=lifespan,
	dependencies=[Depends(verify_internal_key)],
	openapi_tags=[
		{
			"name": "accounts",
			"description": "Операции со счетами: создание, получение списка, управление статусом (заморозка/закрытие).",
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
	rmq_ok = await ping_rabbitmq()

	overall_status = "ok" if db_ok and rmq_ok else "error"
	
	return {
		"status": overall_status,
		"dependencies": {
			"postgres": "ok" if db_ok else "error",
			"rabbitmq": "ok" if rmq_ok else "error",
		},
	}


app.include_router(accounts_router)
