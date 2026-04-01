"""Customer Service — онбординг, управление данными клиента, удаление аккаунта."""

from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI

from shared.config import BaseAppSettings
from shared.bootstrap import bootstrap, get_container

# Инициализация инфраструктуры
bootstrap(BaseAppSettings)
container = get_container()

from shared.rabbitmq import connect as rmq_connect, disconnect as rmq_disconnect
from shared.redis_onboarding import client as redis_onboarding_client
from shared.internal_auth import verify_internal_key
from shared.utils.exceptions_handler import setup_exception_handlers

from .create_account.router import router as onboarding_router
from .delete_account.router import router as delete_account_router
from .update_user_data.router import router as update_user_data_router


@asynccontextmanager
async def lifespan(app: FastAPI):
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
async def health_check() -> dict[str, str]:
	return {"status": "ok"}


app.include_router(onboarding_router)
app.include_router(update_user_data_router)
app.include_router(delete_account_router)
