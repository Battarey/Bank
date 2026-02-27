import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.redis_sessions import client as redis_sessions_client
from shared.redis_onboarding import client as redis_onboarding_client

from .middleware import auth_middleware
from .routes.auth import protected_router as auth_protected_router
from .routes.auth import public_router as auth_public_router
from .routes.customer import onboarding_router, onboarding_steps_router, update_router

CUSTOMER_SERVICE_URL = os.getenv("CUSTOMER_SERVICE_URL")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL")
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS")


@asynccontextmanager
async def lifespan(app: FastAPI):
	async with (
		httpx.AsyncClient(base_url=CUSTOMER_SERVICE_URL, timeout=30.0) as customer,
		httpx.AsyncClient(base_url=AUTH_SERVICE_URL, timeout=30.0) as auth,
	):
		app.state.services = {
			"customer": customer,
			"auth": auth,
		}
		yield
	await redis_sessions_client.close_client()
	await redis_onboarding_client.close_client()


app = FastAPI(title="Gateway Service", version="0.1.0", lifespan=lifespan)

app.add_middleware(
	CORSMiddleware,
	allow_origins=CORS_ALLOWED_ORIGINS,
	allow_credentials=True,
	allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
	allow_headers=["*"],
)

app.middleware("http")(auth_middleware)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
	return {"status": "ok"}


app.include_router(onboarding_router)
app.include_router(onboarding_steps_router)
app.include_router(update_router)
app.include_router(auth_public_router)
app.include_router(auth_protected_router)
