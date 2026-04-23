"""Роутер для получения актуальных курсов валют."""

from fastapi import APIRouter, Query, status

from shared import schemas

from ..services import rates as service

router = APIRouter(
	prefix="/rates",
	tags=["rates"],
)


@router.get(
	"",
	response_model=schemas.ExchangeRatesResponse,
	status_code=status.HTTP_200_OK,
	summary="Все курсы валют",
)
async def get_rates(
	base: str = Query("RUB", min_length=3, max_length=3, description="Код базовой валюты (ISO 4217)"),
):
	"""Возвращает таблицу курсов всех валют относительно указанной базовой валюты."""
	rates, updated = await service.get_all_rates(base.upper())

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
	rate, updated = await service.get_pair_rate(base.upper(), target.upper())

	return schemas.ExchangeRatePairResponse(
		base=base.upper(),
		target=target.upper(),
		rate=rate,
		last_updated=updated,
	)
