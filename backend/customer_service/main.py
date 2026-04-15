"""Customer Service — онбординг, управление данными клиента, удаление аккаунта."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from shared.bootstrap import bootstrap, get_container
from shared.config import BaseAppSettings

# Инициализация инфраструктуры
bootstrap(BaseAppSettings)
container = get_container()

from shared.internal_auth import verify_internal_key
from shared.rabbitmq import connect as rmq_connect
from shared.rabbitmq import disconnect as rmq_disconnect
from shared.redis_onboarding import client as redis_onboarding_client
from shared.utils.exceptions_handler import setup_exception_handlers

from .api.onboarding import router as onboarding_router
from .api.account import router as delete_account_router
from .api.update import router as update_user_data_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
	await rmq_connect()
	yield
	await rmq_disconnect()
	await redis_onboarding_client.close_client()
	await container.dispose()


app = FastAPI(
	title="Customer Service",
	version="0.2.0",
	description="Управление данными клиента: онбординг (KYC), обновление профиля и удаление аккаунта.",
	lifespan=lifespan,
	dependencies=[Depends(verify_internal_key)],
	openapi_tags=[
		{
			"name": "onboarding",
			"description": "Процесс регистрации: пошаговое заполнение данных и финализация.",
		},
		{
			"name": "user-update",
			"description": "Обновление персональных данных, паспорта и контактов активного пользователя.",
		},
		{
			"name": "user-account",
			"description": "Управление аккаунтом (удаление).",
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
	redis_ok = await redis_onboarding_client.ping()
	rmq_ok = await ping_rabbitmq()

	overall_status = "ok" if db_ok and redis_ok and rmq_ok else "error"
	
	return {
		"status": overall_status,
		"dependencies": {
			"postgres": "ok" if db_ok else "error",
			"redis_onboarding": "ok" if redis_ok else "error",
			"rabbitmq": "ok" if rmq_ok else "error",
		},
	}


app.include_router(onboarding_router)
app.include_router(update_user_data_router)
app.include_router(delete_account_router)
