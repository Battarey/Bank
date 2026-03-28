"""Роутер для обмена валюты между банковскими счетами."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared import schemas
from shared.database_core.db import get_session
from shared.internal_auth import require_user_id
from currency_service.exceptions import (
	AccountNotFound,
	AccountNotOpen,
	CurrencyError,
	InsufficientFunds,
	RateUnavailable,
	SameAccountExchange,
	SameCurrencyExchange,
)
from . import service

router = APIRouter(
	prefix="/exchange",
	tags=["exchange"],
)


def _raise(exc: CurrencyError) -> None:
	if isinstance(exc, AccountNotFound):
		raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
	if isinstance(exc, (SameAccountExchange, SameCurrencyExchange)):
		raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
	if isinstance(exc, InsufficientFunds):
		raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
	if isinstance(exc, AccountNotOpen):
		raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
	if isinstance(exc, RateUnavailable):
		raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc))
	raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
	"",
	response_model=schemas.ExchangeResponse,
	status_code=status.HTTP_200_OK,
	summary="Обменять валюту между счетами",
)
async def exchange_currency(
	payload: schemas.ExchangeRequest,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Конвертирует валюту между двумя банковскими счетами пользователя (RUB/USD/EUR)."""
	try:
		from_amount, to_amount, rate = await service.exchange(
			session, user_id,
			from_account_id=payload.from_account_id,
			to_account_id=payload.to_account_id,
			amount=payload.amount,
		)
	except CurrencyError as exc:
		_raise(exc)

	# Получаем валюты счетов для ответа
	from shared import models
	from_account = await session.get(models.BankAccount, payload.from_account_id)
	to_account = await session.get(models.BankAccount, payload.to_account_id)

	return schemas.ExchangeResponse(
		message="Обмен выполнен.",
		from_account_id=payload.from_account_id,
		to_account_id=payload.to_account_id,
		from_amount=from_amount,
		to_amount=to_amount,
		rate=rate,
		from_currency=from_account.currency,
		to_currency=to_account.currency,
	)
