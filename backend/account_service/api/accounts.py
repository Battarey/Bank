"""Роутеры для управления жизненным циклом банковских счетов."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared import schemas
from shared.internal_auth import require_user_id

from ..core.uow import AccountUnitOfWork, get_uow
from ..services import account as service

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
	summary="Список своих счетов",
)
async def list_accounts(
	user_id: UUID = Depends(require_user_id),
	uow: AccountUnitOfWork = Depends(get_uow),
):
	"""Возвращает список всех счетов (активных, закрытых, замороженных) текущего пользователя."""
	accounts, total = await service.list_accounts(uow, user_id)

	return schemas.AccountListResponse(
		accounts=accounts,
		total=total,
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


@router.delete(
	"/{account_id}",
	response_model=schemas.AccountMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Закрыть счёт",
)
async def close_account(
	account_id: UUID,
	user_id: UUID = Depends(require_user_id),
	uow: AccountUnitOfWork = Depends(get_uow),
):
	"""Закрывает банковский счёт текущего пользователя (мягкое удаление).

	Счёт не удаляется физически, а переходит в статус 'closed'.
	Для успешного закрытия баланс должен быть нулевым.
	"""
	account = await service.close_account(uow, user_id, account_id)

	return schemas.AccountMessageResponse(
		message="Счёт успешно закрыт.",
		account=schemas.AccountResponse.model_validate(account),
	)


@router.post(
	"/{account_id}/suspensions",
	response_model=schemas.AccountMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Приостановить обслуживание счёта",
)
async def suspend_account(
	account_id: UUID,
	user_id: UUID = Depends(require_user_id),
	uow: AccountUnitOfWork = Depends(get_uow),
):
	"""Приостанавливает операции по банковскому счёту (заморозка).

	Замороженный счёт недоступен для любых расходных операций (переводы, оплата).
	"""
	account = await service.freeze_account(uow, user_id, account_id)

	return schemas.AccountMessageResponse(
		message="Обслуживание счёта приостановлено.",
		account=schemas.AccountResponse.model_validate(account),
	)


@router.delete(
	"/{account_id}/suspensions",
	response_model=schemas.AccountMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Возобновить обслуживание счёта",
)
async def resume_account(
	account_id: UUID,
	user_id: UUID = Depends(require_user_id),
	uow: AccountUnitOfWork = Depends(get_uow),
):
	"""Снимает приостановку со счёта (разморозка), если она была установлена пользователем."""
	account = await service.unfreeze_account(uow, user_id, account_id)

	return schemas.AccountMessageResponse(
		message="Обслуживание счёта возобновлено.",
		account=schemas.AccountResponse.model_validate(account),
	)
