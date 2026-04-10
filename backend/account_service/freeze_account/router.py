"""Роутер для управления блокировками банковских счетов."""

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
