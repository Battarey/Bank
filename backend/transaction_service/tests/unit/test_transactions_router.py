from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from shared import models, schemas
from transaction_service.transactions.router import create_transaction


def mock_tx(tx_type="deposit"):
	return models.Transaction(
		id=uuid4(),
		account_id=uuid4(),
		type=tx_type,
		amount=Decimal("100"),
		created_at=MagicMock(),
		direction="incoming" if tx_type == "deposit" else "outgoing",
		status="posted",
		balance_before=Decimal("0"),
		balance_after=Decimal("100"),
	)


@pytest.mark.asyncio
@patch("transaction_service.transactions.router.deposit_service.deposit")
async def test_create_deposit_router_success(mock_svc, mock_uow):
	"""Роутер: успешное создание депозита."""
	mock_svc.return_value = mock_tx("deposit")
	user_id = uuid4()

	# Используем конкретный класс вместо Union
	payload = schemas.DepositRequest(account_id=uuid4(), amount=Decimal("100.00"), description="test")

	res = await create_transaction(payload, user_id, mock_uow)

	assert res.transaction.type == "deposit"
	assert "успешно" in res.message
	mock_svc.assert_awaited_once()


@pytest.mark.asyncio
@patch("transaction_service.transactions.router.withdrawal_service.withdraw")
async def test_create_withdrawal_router_success(mock_svc, mock_uow):
	"""Роутер: успешное создание снятия."""
	mock_svc.return_value = mock_tx("withdrawal")
	user_id = uuid4()

	payload = schemas.WithdrawalRequest(account_id=uuid4(), amount=Decimal("50.00"))

	res = await create_transaction(payload, user_id, mock_uow)

	assert res.transaction.type == "withdrawal"
	mock_svc.assert_awaited_once()


@pytest.mark.asyncio
@patch("transaction_service.transactions.router.transfer_service.transfer")
async def test_create_transfer_router_success(mock_svc, mock_uow):
	"""Роутер: успешное создание перевода."""
	mock_svc.return_value = mock_tx("transfer")
	user_id = uuid4()

	payload = schemas.TransferRequest(from_account_id=uuid4(), to_account_id=uuid4(), amount=Decimal("20.00"))

	res = await create_transaction(payload, user_id, mock_uow)

	assert res.transaction.type == "transfer"
	mock_svc.assert_awaited_once()
