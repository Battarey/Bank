"""Маршруты Gateway → Transaction Service (операции по счетам)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from shared import schemas
from gateway_service.helpers import forward_request
from gateway_service.middleware import session_token_scheme

router = APIRouter(
	prefix="/accounts",
	tags=["transactions"],
	dependencies=[Depends(session_token_scheme)],
)


@router.post(
	"/{account_id}/deposit",
	response_model=schemas.TransactionMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Пополнить счёт",
)
async def deposit(
	account_id: UUID,
	payload: schemas.DepositRequest,
	request: Request,
):
	"""Вносит средства на указанный счёт."""
	data = await forward_request(
		request,
		"POST",
		f"/accounts/{account_id}/deposit",
		payload.model_dump(mode="json"),
		service="transaction",
	)
	return data


@router.post(
	"/{account_id}/withdraw",
	response_model=schemas.TransactionMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Снять со счёта",
)
async def withdraw(
	account_id: UUID,
	payload: schemas.WithdrawalRequest,
	request: Request,
):
	"""Списывает средства со счёта текущего пользователя."""
	data = await forward_request(
		request,
		"POST",
		f"/accounts/{account_id}/withdraw",
		payload.model_dump(mode="json"),
		service="transaction",
	)
	return data


@router.post(
	"/{account_id}/transfer",
	response_model=schemas.TransactionMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Перевести между счетами",
)
async def transfer(
	account_id: UUID,
	payload: schemas.TransferRequest,
	request: Request,
):
	"""Переводит средства с указанного счёта на другой (свой или чужой)."""
	data = await forward_request(
		request,
		"POST",
		f"/accounts/{account_id}/transfer",
		payload.model_dump(mode="json"),
		service="transaction",
	)
	return data


@router.get(
	"/{account_id}/transactions",
	response_model=schemas.TransactionListResponse,
	status_code=status.HTTP_200_OK,
	summary="История операций",
)
async def transaction_history(
	account_id: UUID,
	request: Request,
	limit: int = Query(20, ge=1, le=100, description="Кол-во записей на странице"),
	offset: int = Query(0, ge=0, description="Смещение"),
	type: str | None = Query(None, description="Тип операции: deposit | withdrawal | transfer"),
	direction: str | None = Query(None, description="Направление: incoming | outgoing"),
):
	"""Возвращает историю операций по счёту с пагинацией и фильтрами."""
	params = f"?limit={limit}&offset={offset}"
	if type:
		params += f"&type={type}"
	if direction:
		params += f"&direction={direction}"

	data = await forward_request(
		request,
		"GET",
		f"/accounts/{account_id}/transactions{params}",
		service="transaction",
	)
	return data
