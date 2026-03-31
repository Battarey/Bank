"""Transaction Service — операции по банковским счетам: пополнение, снятие, переводы и история."""

from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI

from shared.database_core.db import engine
from shared.internal_auth import verify_internal_key
from shared.rabbitmq.client import connect as rmq_connect, disconnect as rmq_disconnect
from shared.utils.exceptions_handler import setup_exception_handlers

from .transactions.router import router as transactions_router
from .history.router import router as history_router
from . import security_client
from . import currency_client


@asynccontextmanager
async def lifespan(app: FastAPI):
	await rmq_connect()
	await security_client.connect()
	await currency_client.connect()
	yield
	await currency_client.disconnect()
	await security_client.disconnect()
	await rmq_disconnect()
	await engine.dispose()


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
async def health_check() -> dict[str, str]:
	return {"status": "ok"}


app.include_router(transactions_router)
app.include_router(history_router)
