"""Роутер для просмотра курсов валют."""

from fastapi import APIRouter, HTTPException, Query, status

from shared import schemas
from currency_service.exceptions import CurrencyError, CurrencyNotAvailable, RateUnavailable
from . import service

router = APIRouter(
	prefix="/rates",
	tags=["rates"],
)


def _raise(exc: CurrencyError) -> None:
	if isinstance(exc, CurrencyNotAvailable):
		raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
	if isinstance(exc, RateUnavailable):
		raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc))
	raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
	"",
	response_model=schemas.ExchangeRatesResponse,
	status_code=status.HTTP_200_OK,
	summary="Все курсы валют",
)
async def get_rates(
	base: str = Query("RUB", min_length=3, max_length=3, description="Базовая валюта (ISO 4217)"),
):
	"""Возвращает курсы всех валют относительно базовой."""
	try:
		rates, updated = await service.get_all_rates(base.upper())
	except CurrencyError as exc:
		_raise(exc)

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
	"""Возвращает курс конкретной валютной пары."""
	try:
		rate, updated = await service.get_pair_rate(base.upper(), target.upper())
	except CurrencyError as exc:
		_raise(exc)

	return schemas.ExchangeRatePairResponse(
		base=base.upper(),
		target=target.upper(),
		rate=rate,
		last_updated=updated,
	)
