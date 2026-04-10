"""Глобальный обработчик бизнес-исключений для FastAPI."""

from fastapi import Request
from fastapi.responses import JSONResponse

from .exceptions import BaseBusinessError


async def business_exception_handler(_request: Request, exc: BaseBusinessError) -> JSONResponse:
	"""Ловит исключения, наследуемые от BaseBusinessError, и превращает их в RFC 7807 ответ."""

	content = {
		"type": exc.__class__.__name__,
		"title": getattr(exc, "title", "Business Error"),
		"status": exc.status_code,
		"detail": str(exc),
	}

	if exc.details:
		content["details"] = exc.details

	return JSONResponse(
		status_code=exc.status_code,
		content=content,
	)


def setup_exception_handlers(app) -> None:
	"""Регистрирует обработчики исключений в FastAPI приложении."""

	app.add_exception_handler(BaseBusinessError, business_exception_handler)
