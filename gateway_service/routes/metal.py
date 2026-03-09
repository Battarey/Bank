"""Маршруты Gateway → Metal Service (драгоценные металлы)."""

from fastapi import APIRouter, Query, Request, status

from shared import schemas
from gateway_service.helpers import forward_request

public_router = APIRouter(
	prefix="/metals",
	tags=["metals"],
)


@public_router.get(
	"/rates",
	response_model=schemas.MetalRatesListResponse,
	status_code=status.HTTP_200_OK,
	summary="Цены на металлы",
)
async def get_metal_rates(
	request: Request,
	base: str = Query("RUB", min_length=3, max_length=3),
):
	"""Возвращает цены на драгоценные металлы (за грамм)."""
	data = await forward_request(
		request,
		"GET",
		f"/metals/rates?base={base}",
		service="metal",
	)
	return data

