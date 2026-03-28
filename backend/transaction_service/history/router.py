"""Роутер для просмотра истории транзакций."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared import schemas
from shared.database_core.db import get_session
from shared.internal_auth import require_user_id
from transaction_service.exceptions import AccountNotFound, TransactionError
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
	session: AsyncSession = Depends(get_session),
):
	"""Возвращает историю операций по счёту с пагинацией и фильтрами."""

	try:
		transactions, total = await service.list_transactions(
			session, user_id, account_id,
			limit=limit,
			offset=offset,
			tx_type=type,
			direction=direction,
		)
	except AccountNotFound as exc:
		raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
	except TransactionError as exc:
		raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))

	return schemas.TransactionListResponse(
		transactions=[schemas.TransactionResponse.model_validate(tx) for tx in transactions],
		total=total,
		limit=limit,
		offset=offset,
	)
