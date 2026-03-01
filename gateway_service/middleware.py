"""Middleware для аутентификации запросов через X-Session-Token."""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from shared.redis_sessions import dependencies as session_deps

# Схема авторизации для Swagger UI (кнопка "Authorize")
session_token_scheme = APIKeyHeader(
	name="X-Session-Token",
	scheme_name="SessionToken",
	description="Сессионный токен, полученный при авторизации",
	auto_error=False,
)

onboarding_token_scheme = APIKeyHeader(
	name="X-Onboarding-Token",
	scheme_name="OnboardingToken",
	description="Токен онбординга, полученный из /users/start (TTL 15 минут, скользящая экспирация)",
	auto_error=False,
)

# Эндпоинты, не требующие авторизации
PUBLIC_PATHS: set[str] = {
	"/",
	"/health",
	"/docs",
	"/openapi.json",
	"/redoc",
	"/favicon.ico",
	"/auth/login-pin",
	"/auth/request-unlock",
	"/auth/unlock",
}

# Префиксы путей, не требующих авторизации (только онбординг)
PUBLIC_PREFIXES: tuple[str, ...] = (
	"/users/start",
)

# Подстроки, по которым путь считается публичным (шаги онбординга до авторизации)
PUBLIC_SEGMENTS: tuple[str, ...] = (
	"/account/",
)

# Пути, доступные авторизованным пользователям БЕЗ установленного PIN
PIN_EXEMPT_PATHS: set[str] = {
	"/auth/set-pin",
	"/auth/logout",
	"/auth/logout-all",
}


def _is_public(path: str, method: str) -> bool:
	"""Определяет, является ли запрос публичным."""
	return (
		path in PUBLIC_PATHS
		or path.startswith(PUBLIC_PREFIXES)
		or any(seg in path for seg in PUBLIC_SEGMENTS)
		or method == "OPTIONS"
	)


async def auth_middleware(request: Request, call_next):
	"""Проверяет X-Session-Token, извлекает user_id и кладёт его в state.

	Если PIN не установлен (has_pin != true), допускает только
	/auth/set-pin, /auth/logout и /auth/logout-all.
	"""

	if _is_public(request.url.path, request.method):
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

	# Проверка: PIN установлен?
	has_pin = session_data.get("has_pin", "false")
	if has_pin != "true" and request.url.path not in PIN_EXEMPT_PATHS:
		return JSONResponse(
			status_code=403,
			content={"detail": "Необходимо установить PIN-код. POST /auth/set-pin"},
		)

	return await call_next(request)
