"""Роутер для проведения валютно-обменных операций."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models, schemas
from shared.database_core.db import get_session
from shared.internal_auth import require_user_id
from . import service

router = APIRouter(
	prefix="/exchange",
	tags=["exchange"],
)


@router.post(
	"",
	response_model=schemas.ExchangeResponse,
	status_code=status.HTTP_200_OK,
	summary="Обменять валюту",
)
async def exchange_currency(
	payload: schemas.ExchangeRequest,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Конвертирует средства между двумя банковскими счетами текущего пользователя.
	
	Курс обмена запрашивается в реальном времени. Операция атомарна.
	"""
	from_amount, to_amount, rate = await service.exchange(
		session, 
		user_id,
		from_account_id=payload.from_account_id,
		to_account_id=payload.to_account_id,
		amount=payload.amount,
	)

	# Получаем актуальные данные счетов для формирования ответа
	from_account = await session.get(models.BankAccount, payload.from_account_id)
	to_account = await session.get(models.BankAccount, payload.to_account_id)

	return schemas.ExchangeResponse(
		message="Обмен успешно выполнен.",
		from_account_id=payload.from_account_id,
		to_account_id=payload.to_account_id,
		from_amount=from_amount,
		to_amount=to_amount,
		rate=rate,
		from_currency=from_account.currency,
		to_currency=to_account.currency,
	)
