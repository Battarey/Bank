"""Metal Service — получение актуальных котировок драгоценных металлов."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from shared.bootstrap import bootstrap, get_container

from .core.config import MetalSettings

# Инициализация инфраструктуры (Settings, DB Engine, Session Factory)
bootstrap(MetalSettings)
container = get_container()

from shared.internal_auth import verify_internal_key
from shared.utils.exceptions_handler import setup_exception_handlers
from shared.utils.monitoring import instrument_app

from .api.rates import router as rates_router
from .repositories.metal import get_metal_repository


class HealthCheckDependencies(BaseModel):
	"""Состояние зависимостей сервиса."""

	external_metal_api: str = Field(..., json_schema_extra={"example": "ok"})


class HealthCheckResponse(BaseModel):
	"""Формат ответа проверки состояния сервиса."""

	status: str = Field(..., json_schema_extra={"example": "ok"})
	dependencies: HealthCheckDependencies


@asynccontextmanager
async def lifespan(_app: FastAPI):
	repo = get_metal_repository()
	await repo.connect()
	yield
	await repo.disconnect()


app = FastAPI(
	title="Metal Service",
	version="0.2.0",
	description="Сервис получения банковских котировок на драгоценные металлы (Золото, Серебро, Платина, Палладий).",
	lifespan=lifespan,
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


@app.get("/health", tags=["health"], response_model=HealthCheckResponse)
async def health_check() -> dict:
	"""Проверка работоспособности сервиса."""
	# Metal service зависит в основном от внешнего API, которое проверяется в lifespan
	return {
		"status": "ok",
		"dependencies": {
			"external_metal_api": "ok",
		},
	}


# Инструментирование для мониторинга
instrument_app(app)


app.include_router(rates_router, dependencies=[Depends(verify_internal_key)])
