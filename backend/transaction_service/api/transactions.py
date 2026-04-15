"""Унифицированный роутер для всех типов транзакций (пополнение, снятие, перевод)."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared import schemas
from shared.internal_auth import require_user_id

# Переход на новую структуру сервисов
from ..services import deposit as deposit_service
from ..services import transfer as transfer_service
from ..services import withdrawal as withdrawal_service

# Переход на новую структуру core
from ..core.uow import TransactionUnitOfWork, get_uow
from ..core.exceptions import TransactionError

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
	user_id: UUID = Depends(require_user_id),
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
			idempotency_key=payload.idempotency_key,
		)
		message = "Пополнение успешно выполнено."

	elif payload.type == "withdrawal":
		tx = await withdrawal_service.withdraw(
			uow,
			user_id,
			account_id=payload.account_id,
			amount=payload.amount,
			description=payload.description,
			idempotency_key=payload.idempotency_key,
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
			idempotency_key=payload.idempotency_key,
		)
		message = "Перевод успешно выполнен."
	else:
		raise TransactionError("Неверный тип операции")

	return schemas.TransactionMessageResponse(
		message=message,
		transaction=schemas.TransactionResponse.model_validate(tx),
	)
