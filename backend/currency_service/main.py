"""Currency Service — управление курсами валют и конверсионными операциями."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from shared.bootstrap import bootstrap, get_container

from .core.config import CurrencySettings

# Инициализация инфраструктуры (Settings, DB Engine, Session Factory)
bootstrap(CurrencySettings)
container = get_container()

from shared.internal_auth import verify_internal_key
from shared.rabbitmq.client import connect as rmq_connect
from shared.rabbitmq.client import disconnect as rmq_disconnect
from shared.utils.exceptions_handler import setup_exception_handlers

from .api.exchange import router as exchange_router
from .api.rates import router as rates_router
from .clients import exchange_client


@asynccontextmanager
async def lifespan(_app: FastAPI):
	await rmq_connect()
	await exchange_client.connect()
	yield
	await exchange_client.disconnect()
	await rmq_disconnect()
	await container.dispose()


app = FastAPI(
	title="Currency Service",
	version="0.2.0",
	description="Сервис валютных операций: получение актуальных котировок и внутренний обмен между счетами.",
	lifespan=lifespan,
	dependencies=[Depends(verify_internal_key)],
	openapi_tags=[
		{
			"name": "rates",
			"description": "Получение курсов валют в реальном времени.",
		},
		{
			"name": "exchange",
			"description": "Операции обмена валют между банковскими счетами.",
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
	from shared.rabbitmq.client import ping_rabbitmq

	rmq_ok = await ping_rabbitmq()

	overall_status = "ok" if rmq_ok else "error"
	
	return {
		"status": overall_status,
		"dependencies": {
			"rabbitmq": "ok" if rmq_ok else "error",
		},
	}


app.include_router(rates_router)
app.include_router(exchange_router)
