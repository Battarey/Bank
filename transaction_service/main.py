"""Transaction Service — операции по банковским счетам: пополнение, снятие, переводы."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from shared.database_core.db import engine
from shared.internal_auth import verify_internal_key
from shared.rabbitmq.client import connect as rmq_connect, disconnect as rmq_disconnect

from .deposit.router import router as deposit_router
from .withdrawal.router import router as withdrawal_router
from .transfer.router import router as transfer_router
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
	version="0.1.0",
	description="Внутренний сервис транзакций: пополнение, снятие, переводы, история.",
	lifespan=lifespan,
	dependencies=[Depends(verify_internal_key)],
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
	return {"status": "ok"}


app.include_router(deposit_router)
app.include_router(withdrawal_router)
app.include_router(transfer_router)
app.include_router(history_router)
