from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from shared.database_core.db import engine

from .open_account.router import router as open_account_router
from .close_account.router import router as close_account_router


@asynccontextmanager
async def lifespan(app: FastAPI):
	yield
	await engine.dispose()


app = FastAPI(
	title="Account Service",
	version="0.1.0",
	description="Сервис банковских счетов: открытие, просмотр и закрытие.",
	lifespan=lifespan,
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
	return {"status": "ok"}


app.include_router(open_account_router)
app.include_router(close_account_router)
