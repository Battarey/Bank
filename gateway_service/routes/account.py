"""Маршруты Gateway → Account Service (банковские счета)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from shared import schemas
from gateway_service.helpers import forward_request
from gateway_service.middleware import session_token_scheme

router = APIRouter(
	prefix="/accounts",
	tags=["accounts"],
	dependencies=[Depends(session_token_scheme)],
)


@router.post(
	"",
	response_model=schemas.AccountMessageResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Открыть новый счёт",
)
async def open_account(
	payload: schemas.OpenAccountRequest,
	request: Request,
):
	"""Создаёт банковский счёт указанного типа и валюты для текущего пользователя."""
	data = await forward_request(
		request,
		"POST",
		"/accounts",
		payload.model_dump(mode="json"),
		service="account",
	)
	return data


@router.get(
	"",
	response_model=schemas.AccountListResponse,
	status_code=status.HTTP_200_OK,
	summary="Список счетов",
)
async def list_accounts(request: Request):
	"""Возвращает все счета текущего пользователя."""
	data = await forward_request(
		request,
		"GET",
		"/accounts",
		service="account",
	)
	return data


@router.get(
	"/{account_id}",
	response_model=schemas.AccountResponse,
	status_code=status.HTTP_200_OK,
	summary="Детали счёта",
)
async def get_account(account_id: UUID, request: Request):
	"""Возвращает данные конкретного счёта."""
	data = await forward_request(
		request,
		"GET",
		f"/accounts/{account_id}",
		service="account",
	)
	return data


@router.post(
	"/{account_id}/close",
	response_model=schemas.AccountMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Закрыть счёт",
)
async def close_account(account_id: UUID, request: Request):
	"""Закрывает банковский счёт. Баланс должен быть 0."""
	data = await forward_request(
		request,
		"POST",
		f"/accounts/{account_id}/close",
		service="account",
	)
	return data
