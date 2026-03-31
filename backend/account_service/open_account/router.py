"""Роутер для управления банковскими счетами: открытие, листинг и детализация."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared import schemas
from shared.internal_auth import require_user_id
from ..uow import AccountUnitOfWork, get_uow
from . import service

router = APIRouter(
	prefix="/accounts",
	tags=["accounts"],
)


@router.post(
	"",
	response_model=schemas.AccountMessageResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Открыть новый счёт",
)
async def open_account(
	payload: schemas.OpenAccountRequest,
	user_id: UUID = Depends(require_user_id),
	uow: AccountUnitOfWork = Depends(get_uow),
):
	"""Создаёт новый банковский счёт указанного типа и валюты для текущего пользователя."""
	account = await service.open_account(uow, user_id, payload)
	
	return schemas.AccountMessageResponse(
		message="Счёт успешно открыт.",
		account=schemas.AccountResponse.model_validate(account),
	)


@router.get(
	"",
	response_model=schemas.AccountListResponse,
	status_code=status.HTTP_200_OK,
	summary="Список моих счетов",
)
async def list_accounts(
	user_id: UUID = Depends(require_user_id),
	uow: AccountUnitOfWork = Depends(get_uow),
):
	"""Возвращает список всех счетов (активных, закрытых, замороженных) текущего пользователя."""
	accounts = await service.list_accounts(uow, user_id)
	
	return schemas.AccountListResponse(
		accounts=[schemas.AccountResponse.model_validate(a) for a in accounts],
		total=len(accounts),
	)


@router.get(
	"/{account_id}",
	response_model=schemas.AccountResponse,
	status_code=status.HTTP_200_OK,
	summary="Информация о счёте",
)
async def get_account(
	account_id: UUID,
	user_id: UUID = Depends(require_user_id),
	uow: AccountUnitOfWork = Depends(get_uow),
):
	"""Возвращает детальную информацию о конкретном счёте по его ID."""
	return await service.get_account(uow, user_id, account_id)
