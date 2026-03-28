"""Роутер для просмотра цен на драгоценные металлы."""

from fastapi import APIRouter, HTTPException, Query, status

from shared import schemas
from metal_service.exceptions import MetalError, RateUnavailable
from metal_service.metal_client import METAL_NAMES
from . import service

router = APIRouter(
	prefix="/metals/rates",
	tags=["metal-rates"],
)


@router.get(
	"",
	response_model=schemas.MetalRatesListResponse,
	status_code=status.HTTP_200_OK,
	summary="Цены на металлы",
)
async def get_metal_rates(
	base: str = Query("RUB", min_length=3, max_length=3, description="Валюта цены (ISO 4217)"),
):
	"""Возвращает цены на драгоценные металлы (за грамм) в указанной валюте."""
	try:
		prices, updated = await service.get_all_prices(base.upper())
	except RateUnavailable as exc:
		raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc))

	rates = [
		schemas.MetalRateResponse(
			metal=metal,
			price_per_gram=price,
			base_currency=base.upper(),
			last_updated=updated,
		)
		for metal, price in prices.items()
	]

	return schemas.MetalRatesListResponse(
		rates=rates,
		base_currency=base.upper(),
		last_updated=updated,
	)
