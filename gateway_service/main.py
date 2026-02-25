import os
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from shared.redis_sessions import dependencies as session_deps, client as redis_client
from .routes.customer import router as customer_router

CUSTOMER_SERVICE_URL = os.getenv("CUSTOMER_SERVICE_URL")
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS")

# Эндпоинты, не требующие авторизации
PUBLIC_PATHS: set[str] = {
	"/",
	"/health",
	"/docs",
	"/openapi.json",
	"/redoc",
	"/favicon.ico",
}

# Префиксы путей, не требующих авторизации (онбординг и т.д.)
PUBLIC_PREFIXES: tuple[str, ...] = (
	"/users/start",
	"/users/",  # все /users/{id}/account/* — онбординг до авторизации
)


@asynccontextmanager
async def lifespan(app: FastAPI):
	async with httpx.AsyncClient(base_url=CUSTOMER_SERVICE_URL, timeout=30.0) as client:
		app.state.http_client = client
		yield
	await redis_client.close_client()


app = FastAPI(title="Gateway Service", version="0.1.0", lifespan=lifespan)

app.add_middleware(
	CORSMiddleware,
	allow_origins=CORS_ALLOWED_ORIGINS,
	allow_credentials=True,
	allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
	allow_headers=["*"],
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
	"""Проверяет X-Session-Token, извлекает user_id и кладёт его в state."""

	# Пропускаем публичные эндпоинты и preflight-запросы
	path = request.url.path
	if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES) or request.method == "OPTIONS":
		return await call_next(request)

	token = request.headers.get("X-Session-Token")
	try:
		session_data = await session_deps.authenticate_token(token)
	except HTTPException as exc:
		return JSONResponse(
			status_code=exc.status_code,
			content={"detail": exc.detail},
		)
	request.state.user_id = session_data["user_id"]
	return await call_next(request)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
	return {"status": "ok"}


app.include_router(customer_router)
