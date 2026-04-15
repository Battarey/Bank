"""Роутер для получения актуальных курсов валют."""

from fastapi import APIRouter, HTTPException, Query, status

from shared import schemas

from ..core.exceptions import CurrencyNotAvailable, RateUnavailable
from ..services import rates as service

router = APIRouter(
	prefix="/rates",
	tags=["rates"],
)


@router.get(
	"",
	# response_model=schemas.ExchangeRatesResponse,
	response_model=schemas.ExchangeRatesResponse,
	status_code=status.HTTP_200_OK,
	summary="Все курсы валют",
)
async def get_rates(
	base: str = Query("RUB", min_length=3, max_length=3, description="Код базовой валюты (ISO 4217)"),
):
	"""Возвращает таблицу курсов всех валют относительно указанной базовой валюты."""
	try:
		rates, updated = await service.get_all_rates(base.upper())
	except RateUnavailable as exc:
		raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

	return schemas.ExchangeRatesResponse(
		base=base.upper(),
		rates=rates,
		last_updated=updated,
	)


@router.get(
	"/{base}/{target}",
	response_model=schemas.ExchangeRatePairResponse,
	status_code=status.HTTP_200_OK,
	summary="Курс валютной пары",
)
async def get_pair_rate(base: str, target: str):
	"""Возвращает точный курс обмена для конкретной валютной пары (например, RUB/USD)."""
	try:
		rate, updated = await service.get_pair_rate(base.upper(), target.upper())
	except RateUnavailable as exc:
		raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
	except CurrencyNotAvailable as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

	return schemas.ExchangeRatePairResponse(
		base=base.upper(),
		target=target.upper(),
		rate=rate,
		last_updated=updated,
	)
