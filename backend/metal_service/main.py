"""Metal Service — получение актуальных котировок драгоценных металлов."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from shared.bootstrap import bootstrap, get_container

from .config import MetalSettings

# Инициализация инфраструктуры (Settings, DB Engine, Session Factory)
bootstrap(MetalSettings)
container = get_container()

from shared.internal_auth import verify_internal_key
from shared.utils.exceptions_handler import setup_exception_handlers

from . import metal_client
from .rates.router import router as rates_router


@asynccontextmanager
async def lifespan(app: FastAPI):
	await metal_client.connect()
	yield
	await metal_client.disconnect()


app = FastAPI(
	title="Metal Service",
	version="0.2.0",
	description="Сервис получения банковских котировок на драгоценные металлы (Золото, Серебро, Платина, Палладий).",
	lifespan=lifespan,
	dependencies=[Depends(verify_internal_key)],
	openapi_tags=[
		{
			"name": "metal-rates",
			"description": "Получение актуальных цен на драгметаллы.",
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


app.include_router(rates_router)
