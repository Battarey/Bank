"""Metal Service — курсы драгоценных металлов."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from shared.internal_auth import verify_internal_key

from . import metal_client
from .rates.router import router as rates_router


@asynccontextmanager
async def lifespan(app: FastAPI):
	await metal_client.connect()
	yield
	await metal_client.disconnect()


app = FastAPI(
	title="Metal Service",
	version="0.1.0",
	description="Внутренний сервис: цены на драгоценные металлы.",
	lifespan=lifespan,
	dependencies=[Depends(verify_internal_key)],
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
	return {"status": "ok"}


app.include_router(rates_router)
