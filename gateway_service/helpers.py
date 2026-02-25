"""Общие утилиты для пересылки запросов во внутренние сервисы."""

import os

import httpx
from fastapi import HTTPException, Request

INTERNAL_API_KEY: str = os.getenv("INTERNAL_API_KEY", "")


async def forward_request(
	request: Request,
	method: str,
	path: str,
	payload: dict | None = None,
) -> dict:
	"""Пересылает запрос во внутренний сервис и возвращает JSON-ответ."""

	client: httpx.AsyncClient = request.app.state.http_client

	headers = {"X-Internal-Key": INTERNAL_API_KEY}

	# Передаём user_id из сессии во внутренний сервис через заголовок
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
