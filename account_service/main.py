"""Account Service — банковские счета: открытие, просмотр, закрытие."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from shared.database_core.db import engine
from shared.internal_auth import verify_internal_key
from shared.rabbitmq.client import connect as rmq_connect, disconnect as rmq_disconnect

from .open_account.router import router as open_account_router
from .close_account.router import router as close_account_router
from .freeze_account.router import router as freeze_account_router


@asynccontextmanager
async def lifespan(app: FastAPI):
	await rmq_connect()
	yield
	await rmq_disconnect()
	await engine.dispose()


app = FastAPI(
	title="Account Service",
	version="0.2.0",
	description="Внутренний сервис банковских счетов: открытие, просмотр и закрытие.",
	lifespan=lifespan,
	dependencies=[Depends(verify_internal_key)],
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
	return {"status": "ok"}


app.include_router(open_account_router)
app.include_router(close_account_router)
app.include_router(freeze_account_router)
