"""Security Service — AML / антифрод-проверки операций по счетам."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from shared.database_core.db import engine
from shared.internal_auth import verify_internal_key
from shared.rabbitmq.client import connect as rmq_connect, disconnect as rmq_disconnect

from .check.router import router as check_router
from .store import init_mongo, close_mongo


@asynccontextmanager
async def lifespan(app: FastAPI):
	await rmq_connect()
	await init_mongo()
	yield
	await close_mongo()
	await rmq_disconnect()
	await engine.dispose()


app = FastAPI(
	title="Security Service",
	version="0.1.0",
	description="Внутренний сервис безопасности: AML-правила, обнаружение подозрительных операций.",
	lifespan=lifespan,
	dependencies=[Depends(verify_internal_key)],
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
	return {"status": "ok"}


app.include_router(check_router)
