"""Auth Service — аутентификация: OTP + PIN."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from shared.internal_auth import verify_internal_key
from shared.redis_sessions import client as redis_client

from .login.router import router as login_router
from .session.router import router as session_router


@asynccontextmanager
async def lifespan(app: FastAPI):
	yield
	await redis_client.close_client()


app = FastAPI(
	title="Auth Service",
	version="0.1.0",
	lifespan=lifespan,
	dependencies=[Depends(verify_internal_key)],
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
	return {"status": "ok"}


app.include_router(login_router)
app.include_router(session_router)
