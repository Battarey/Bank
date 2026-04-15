"""Transaction Service — операции по банковским счетам: пополнение, снятие, переводы и история."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from shared.bootstrap import bootstrap, get_container

from .core.config import TransactionSettings

# Инициализация инфраструктуры (Settings, DB Engine, Session Factory)
bootstrap(TransactionSettings)
container = get_container()

from shared.internal_auth import verify_internal_key
from shared.rabbitmq.client import connect as rmq_connect
from shared.rabbitmq.client import disconnect as rmq_disconnect
from shared.utils.exceptions_handler import setup_exception_handlers

from .clients import currency as currency_client
from .clients import security as security_client
from .api.history import router as history_router
from .api.transactions import router as transactions_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
	await rmq_connect()
	await security_client.connect()
	await currency_client.connect()
	yield
	await currency_client.disconnect()
	await security_client.disconnect()
	await rmq_disconnect()
	await container.dispose()


app = FastAPI(
	title="Transaction Service",
	version="0.2.1",
	description="Сервис управления финансовыми операциями: переводы, пополнение, снятие и мониторинг истории.",
	lifespan=lifespan,
	dependencies=[Depends(verify_internal_key)],
	openapi_tags=[
		{
			"name": "transactions",
			"description": "Финансовые операции и история транзакций по банковским счетам.",
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


app.include_router(transactions_router)
app.include_router(history_router)
