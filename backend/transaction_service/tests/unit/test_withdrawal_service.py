from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from shared import models
from transaction_service.services.withdrawal import withdraw


@pytest.mark.asyncio
@patch("transaction_service.clients.security.check_transaction")
async def test_withdraw_success(mock_check, mock_uow):
	"""Успешное снятие средств со счёта."""
	user_id = uuid4()
	account_id = uuid4()

	mock_account = MagicMock(spec=models.BankAccount)
	mock_account.id = account_id
	mock_account.client_id = user_id
	mock_account.status = "open"
	mock_account.balance = Decimal("1000.00")
	mock_account.currency = "RUB"
	mock_account.account_number = "123"

	mock_uow.transactions.get_by_idempotency_key.return_value = None
	mock_uow.transactions.get_account_for_update.return_value = mock_account
	mock_uow.transactions.get_owner_contact.return_value = MagicMock(email="test@test.com")

	# Антифрод разрешает
	mock_check.return_value = (True, [])

	amount = Decimal("400.00")
	tx = await withdraw(mock_uow, user_id, account_id, amount, "Test withdraw")

	assert mock_account.balance == Decimal("600.00")
	assert tx.type == "withdrawal"
	mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
@patch("transaction_service.clients.security.check_transaction")
async def test_withdraw_security_violation(mock_check, mock_uow):
	"""Антифрод блокирует снятие — счёт замораживается."""
	user_id = uuid4()
	account_id = uuid4()

	mock_account = MagicMock(spec=models.BankAccount)
	mock_account.client_id = user_id
	mock_account.status = "open"
	mock_account.balance = Decimal("1000.00")
	mock_uow.transactions.get_account_for_update.return_value = mock_account

	# Антифрод блокирует
	mock_check.return_value = (False, [{"rule": "daily_limit"}])

	from transaction_service.core.exceptions import SecurityViolation

	with pytest.raises(SecurityViolation):
		await withdraw(mock_uow, user_id, account_id, Decimal("100"), "desc")

	assert mock_account.status == "frozen"
	assert "AML: daily_limit" in mock_account.freeze_reason
	# Важно: коммит должен был произойти для фиксации блокировки
	mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_withdraw_insufficient_funds(mock_uow):
	"""Ошибка: недостаточно средств."""
	user_id = uuid4()
	account_id = uuid4()

	mock_account = MagicMock(spec=models.BankAccount)
	mock_account.client_id = user_id
	mock_account.status = "open"
	mock_account.balance = Decimal("50.00")
	mock_uow.transactions.get_account_for_update.return_value = mock_account

	with patch("transaction_service.clients.security.check_transaction", AsyncMock(return_value=(True, []))):
		from transaction_service.core.exceptions import InsufficientFunds

		with pytest.raises(InsufficientFunds):
			await withdraw(mock_uow, user_id, account_id, Decimal("100"), "desc")
