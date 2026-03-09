"""Маршруты Gateway → Currency Service (валютные операции)."""

from fastapi import APIRouter, Depends, Query, Request, status

from shared import schemas
from gateway_service.helpers import forward_request
from gateway_service.middleware import session_token_scheme

public_router = APIRouter(
	prefix="/currency",
	tags=["currency"],
)

protected_router = APIRouter(
	prefix="/currency",
	tags=["currency"],
	dependencies=[Depends(session_token_scheme)],
)


# ── Публичные (просмотр курсов) ────────────────────────────────────────

@public_router.get(
	"/rates",
	response_model=schemas.ExchangeRatesResponse,
	status_code=status.HTTP_200_OK,
	summary="Все курсы валют",
)
async def get_rates(
	request: Request,
	base: str = Query("RUB", min_length=3, max_length=3),
):
	"""Возвращает курсы всех валют относительно базовой."""
	data = await forward_request(
		request,
		"GET",
		f"/rates?base={base}",
		service="currency",
	)
	return data


@public_router.get(
	"/rates/{base}/{target}",
	response_model=schemas.ExchangeRatePairResponse,
	status_code=status.HTTP_200_OK,
	summary="Курс валютной пары",
)
async def get_pair_rate(base: str, target: str, request: Request):
	"""Возвращает курс конкретной валютной пары."""
	data = await forward_request(
		request,
		"GET",
		f"/rates/{base}/{target}",
		service="currency",
	)
	return data


# ── Защищённые (обмен между счетами) ──────────────────────────────────

@protected_router.post(
	"/exchange",
	response_model=schemas.ExchangeResponse,
	status_code=status.HTTP_200_OK,
	summary="Обменять валюту между счетами",
)
async def exchange_currency(
	payload: schemas.ExchangeRequest,
	request: Request,
):
	"""Конвертирует валюту между банковскими счетами (RUB/USD/EUR)."""
	data = await forward_request(
		request,
		"POST",
		"/exchange",
		payload.model_dump(mode="json"),
		service="currency",
	)
	return data
