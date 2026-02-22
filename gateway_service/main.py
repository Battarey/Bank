import os
from contextlib import asynccontextmanager
from uuid import UUID
import httpx
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from shared import schemas
from shared.redis_sessions import dependencies as session_deps, client as redis_client

CUSTOMER_SERVICE_URL = os.getenv("CUSTOMER_SERVICE_URL")
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS")

# Эндпоинты, не требующие авторизации
PUBLIC_PATHS: set[str] = {
	"/health",
	"/docs",
	"/openapi.json",
	"/redoc",
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
	session_data = await session_deps.authenticate_token(token)
	request.state.user_id = session_data["user_id"]
	return await call_next(request)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
	return {"status": "ok"}


async def _forward_request(
	request: Request,
	method: str,
	path: str,
	payload: dict | None = None,
) -> dict:
	client: httpx.AsyncClient = request.app.state.http_client

	# Передаём user_id из сессии во внутренний сервис через заголовок
	headers = {}
	user_id = getattr(request.state, "user_id", None)
	if user_id:
		headers["X-User-ID"] = str(user_id)

	response = await client.request(
		method=method,
		url=path,
		json=payload,
		headers=headers,
	)
	if response.status_code >= 400:
		try:
			detail = response.json()
		except ValueError:  # non-json error
			detail = response.text or "Upstream service error"
		raise HTTPException(status_code=response.status_code, detail=detail)
	if response.headers.get("content-type", "").startswith("application/json"):
		return response.json()
	return {}


@app.post(
	"/users/start",
	response_model=schemas.StartOnboardingResponse,
	status_code=status.HTTP_201_CREATED,
)
async def start_onboarding(request: Request):
	data = await _forward_request(
		request,
		"POST",
		"/users/start",
	)
	return schemas.StartOnboardingResponse.model_validate(data)


@app.post(
	"/users/{user_id}/account/personal-data",
	response_model=schemas.PersonalDataResponse,
	status_code=status.HTTP_201_CREATED,
)
async def submit_personal_data(
	user_id: UUID,
	payload: schemas.PersonalDataPayload,
	request: Request,
):
	data = await _forward_request(
		request,
		"POST",
		f"/users/{user_id}/account/personal-data",
		payload.model_dump(mode="json"),
	)
	return schemas.PersonalDataResponse.model_validate(data)


@app.post(
	"/users/{user_id}/account/passport",
	response_model=schemas.PassportResponse,
	status_code=status.HTTP_201_CREATED,
)
async def submit_passport_data(
	user_id: UUID,
	payload: schemas.PassportPayload,
	request: Request,
):
	data = await _forward_request(
		request,
		"POST",
		f"/users/{user_id}/account/passport",
		payload.model_dump(mode="json"),
	)
	return schemas.PassportResponse.model_validate(data)


@app.post(
	"/users/{user_id}/account/identifiers",
	response_model=schemas.IdentifiersResponse,
	status_code=status.HTTP_201_CREATED,
)
async def submit_identifiers(
	user_id: UUID,
	payload: schemas.IdentifiersPayload,
	request: Request,
):
	data = await _forward_request(
		request,
		"POST",
		f"/users/{user_id}/account/identifiers",
		payload.model_dump(mode="json"),
	)
	return schemas.IdentifiersResponse.model_validate(data)


@app.post(
	"/users/{user_id}/account/contacts",
	response_model=schemas.ContactsResponse,
	status_code=status.HTTP_201_CREATED,
)
async def submit_contacts(
	user_id: UUID,
	payload: schemas.ContactsPayload,
	request: Request,
):
	data = await _forward_request(
		request,
		"POST",
		f"/users/{user_id}/account/contacts",
		payload.model_dump(mode="json"),
	)
	return schemas.ContactsResponse.model_validate(data)


@app.post(
	"/users/{user_id}/account/finalize",
	response_model=schemas.FinalizeResponse,
	status_code=status.HTTP_200_OK,
)
async def finalize_onboarding(
	user_id: UUID,
	request: Request,
):
	data = await _forward_request(
		request,
		"POST",
		f"/users/{user_id}/account/finalize",
	)
	return schemas.FinalizeResponse.model_validate(data)
