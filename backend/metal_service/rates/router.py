"""Роутер для просмотра текущих цен на драгоценные металлы."""

from fastapi import APIRouter, Query, status

from shared import schemas
from . import service

router = APIRouter(
	prefix="/metals/rates",
	tags=["metal-rates"],
)


@router.get(
	"",
	response_model=schemas.MetalRatesListResponse,
	status_code=status.HTTP_200_OK,
	summary="Котировки металлов",
)
async def get_metal_rates(
	base: str = Query("RUB", min_length=3, max_length=3, description="Валюта цены (ISO 4217)"),
):
	"""Возвращает актуальные банковские цены за грамм драгоценных металлов в указанной валюте."""
	prices, updated = await service.get_all_prices(base.upper())

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
