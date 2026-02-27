from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from shared.redis_onboarding import client as redis_onboarding_client
from shared.internal_auth import verify_internal_key
from .create_account.router import (
	router as create_account_router,
	start_router as create_account_start_router,
)
from .delete_account.router import router as delete_account_router
from .update_user_data.router import router as update_user_data_router


@asynccontextmanager
async def lifespan(app: FastAPI):
	yield
	await redis_onboarding_client.close_client()


app = FastAPI(
	title="Customer Service",
	version="0.1.0",
	description="Внутренний сервис управления данными клиента: онбординг, KYC, обновление профиля.",
	lifespan=lifespan,
	dependencies=[Depends(verify_internal_key)],
	openapi_tags=[
		{
			"name": "user-account",
			"description": "Онбординг: создание пользователя, пошаговое заполнение данных и финализация.",
		},
		{
			"name": "user-update",
			"description": "Обновление персональных данных, паспорта и контактов авторизованного пользователя.",
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

app.include_router(create_account_start_router)
app.include_router(create_account_router)
app.include_router(delete_account_router)
app.include_router(update_user_data_router)
