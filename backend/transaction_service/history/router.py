"""Роутер для просмотра истории транзакций по банковским счетам."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from shared import schemas
from shared.internal_auth import require_user_id

from ..uow import TransactionUnitOfWork, get_uow
from . import service

router = APIRouter(
	prefix="/accounts",
	tags=["transactions"],
)


@router.get(
	"/{account_id}/transactions",
	response_model=schemas.TransactionListResponse,
	status_code=status.HTTP_200_OK,
	summary="История транзакций",
)
async def list_transactions(
	account_id: UUID,
	limit: int = Query(default=20, ge=1, le=100, description="Записей на страницу"),
	offset: int = Query(default=0, ge=0, description="Смещение"),
	type: str | None = Query(default=None, description="Фильтр: deposit / withdrawal / transfer"),
	direction: str | None = Query(default=None, description="Фильтр: incoming / outgoing"),
	user_id: UUID = Depends(require_user_id),
	uow: TransactionUnitOfWork = Depends(get_uow),
):
	"""Возвращает историю операций по конкретному счёту с поддержкой пагинации и фильтров по типам/направлению."""
	transactions, total = await service.list_transactions(
		uow, 
		user_id, 
		account_id,
		limit=limit,
		offset=offset,
		tx_type=type,
		direction=direction,
	)
	
	return schemas.TransactionListResponse(
		transactions=transactions,
		total=total,
		limit=limit,
		offset=offset,
	)
