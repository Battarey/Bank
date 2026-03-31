"""Унифицированный роутер для всех типов транзакций (пополнение, снятие, перевод)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared import schemas
from shared.internal_auth import require_user_id
from ..uow import TransactionUnitOfWork, get_uow
from ..deposit import service as deposit_service
from ..withdrawal import service as withdrawal_service
from ..transfer import service as transfer_service

router = APIRouter(
	prefix="/transactions",
	tags=["transactions"],
)


@router.post(
	"",
	response_model=schemas.TransactionMessageResponse,
	status_code=status.HTTP_200_OK,
	summary="Выполнить финансовую операцию",
)
async def create_transaction(
	payload: schemas.TransactionCreateRequest,
	user_id: schemas.UUID = Depends(require_user_id),
	uow: TransactionUnitOfWork = Depends(get_uow),
):
	"""Создаёт новую транзакцию (пополнение, снятие или перевод).
	
	Тип операции определяется полем 'type'. Все идентификаторы счетов передаются в теле запроса.
	"""
	if payload.type == "deposit":
		tx = await deposit_service.deposit(
			uow, 
			user_id,
			account_id=payload.account_id,
			amount=payload.amount,
			description=payload.description,
		)
		message = "Пополнение успешно выполнено."
		
	elif payload.type == "withdrawal":
		tx = await withdrawal_service.withdraw(
			uow, 
			user_id,
			account_id=payload.account_id,
			amount=payload.amount,
			description=payload.description,
		)
		message = "Снятие успешно выполнено."
		
	elif payload.type == "transfer":
		tx = await transfer_service.transfer(
			uow, 
			user_id,
			from_account_id=payload.from_account_id,
			to_account_id=payload.to_account_id,
			amount=payload.amount,
			description=payload.description,
		)
		message = "Перевод успешно выполнен."
	else:
		# На случай если Discriminated Union пропустит что-то не то
		from fastapi import HTTPException
		raise HTTPException(status_code=400, detail="Неверный тип операции")

	return schemas.TransactionMessageResponse(
		message=message,
		transaction=schemas.TransactionResponse.model_validate(tx),
	)
