"""Роутер для проведения валютно-обменных операций."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models, schemas
from .uow import CurrencyUnitOfWork, get_uow
from . import service

router = APIRouter(
	prefix="/currency-conversions",
	tags=["conversions"],
)


@router.post(
	"",
	# response_model=schemas.ExchangeResponse,
	response_model=schemas.ExchangeResponse,
	status_code=status.HTTP_200_OK,
	summary="Конвертировать валюту",
)
async def convert_currency(
	payload: schemas.ExchangeRequest,
	user_id: UUID = Depends(require_user_id),
	uow: CurrencyUnitOfWork = Depends(get_uow),
):
	"""Конвертирует средства между двумя банковскими счетами разных валют текущего пользователя.
	
	Курс конвертации запрашивается в реальном времени. Операция атомарна.

	Args:
		payload: Схема запроса с ID счетов и суммой.
		user_id: ID текущего пользователя (из токена).
		uow: Unit of Work для управления транзакцией.

	Returns:
		schemas.ExchangeResponse: Результат конвертации с деталями списания и зачисления.
	"""
	from_amount, to_amount, rate = await service.exchange(
		uow, 
		user_id,
		from_account_id=payload.from_account_id,
		to_account_id=payload.to_account_id,
		amount=payload.amount,
	)

	# Получаем актуальные данные счетов для формирования ответа
	async with uow:
		from_account = await uow.accounts.get_by_user(user_id, payload.from_account_id)
		to_account = await uow.accounts.get_by_user(user_id, payload.to_account_id)

	return schemas.ExchangeResponse(
		message="Конвертация успешно выполнена.",
		from_account_id=payload.from_account_id,
		to_account_id=payload.to_account_id,
		from_amount=from_amount,
		to_amount=to_amount,
		rate=rate,
		from_currency=from_account.currency,
		to_currency=to_account.currency,
	)
