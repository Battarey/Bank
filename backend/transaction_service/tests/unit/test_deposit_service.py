from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from shared import models
from transaction_service.services.deposit import deposit


@pytest.mark.asyncio
async def test_deposit_success(mock_uow):
	"""Успешное пополнение счёта."""
	user_id = uuid4()
	account_id = uuid4()

	# Мокаем данные счета
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

	# Выполнение
	amount = Decimal("500.00")
	tx = await deposit(mock_uow, user_id, account_id, amount, "Test deposit")

	# Проверки
	assert mock_account.balance == Decimal("1500.00")
	assert tx.type == "deposit"
	assert tx.amount == amount

	mock_uow.transactions.add.assert_called_once()
	mock_uow.commit.assert_awaited_once()
	mock_uow.add_event.assert_called()  # Лог + Уведомление


@pytest.mark.asyncio
async def test_deposit_wrong_owner(mock_uow):
	"""Ошибка: счёт не принадлежит пользователю."""
	user_id = uuid4()
	other_user_id = uuid4()
	account_id = uuid4()

	mock_account = MagicMock(spec=models.BankAccount)
	mock_account.client_id = other_user_id
	mock_uow.transactions.get_account_for_update.return_value = mock_account

	from transaction_service.core.exceptions import AccountNotFound

	with pytest.raises(AccountNotFound, match="Счёт не принадлежит вам"):
		await deposit(mock_uow, user_id, account_id, Decimal("100"), "desc")


@pytest.mark.asyncio
async def test_deposit_idempotency(mock_uow):
	"""Идемпотентность: возврат существующей транзакции."""
	user_id = uuid4()
	account_id = uuid4()
	i_key = uuid4()

	mock_tx = MagicMock()
	mock_uow.transactions.get_by_idempotency_key.return_value = mock_tx

	tx = await deposit(mock_uow, user_id, account_id, Decimal("100"), "desc", idempotency_key=i_key)

	assert tx == mock_tx
	mock_uow.transactions.get_account_for_update.assert_not_called()
