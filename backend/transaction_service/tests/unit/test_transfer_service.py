from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from shared import models
from transaction_service.services.transfer import transfer


@pytest.mark.asyncio
@patch("transaction_service.clients.security.check_transaction")
async def test_transfer_success_same_currency(mock_check, mock_uow):
	"""Успешный перевод между счетами в одной валюте."""
	user_id = uuid4()
	from_id, to_id = uuid4(), uuid4()

	mock_from = MagicMock(spec=models.BankAccount)
	mock_from.id, mock_from.client_id, mock_from.status = from_id, user_id, "open"
	mock_from.balance, mock_from.currency = Decimal("1000"), "RUB"

	mock_to = MagicMock(spec=models.BankAccount)
	mock_to.id, mock_to.status = to_id, "open"
	mock_to.balance, mock_to.currency = Decimal("500"), "RUB"

	mock_uow.transactions.lock_accounts.return_value = {from_id: mock_from, to_id: mock_to}
	mock_uow.transactions.get_owner_contact.return_value = MagicMock(email="sender@test.com")
	mock_check.return_value = (True, [])

	tx = await transfer(mock_uow, user_id, from_id, to_id, Decimal("300"), "Present")

	assert mock_from.balance == Decimal("700")
	assert mock_to.balance == Decimal("800")
	assert tx.type == "transfer"
	mock_uow.transactions.add_all.assert_called_once()
	mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
@patch("transaction_service.clients.currency.get_rate")
@patch("transaction_service.clients.security.check_transaction")
async def test_transfer_with_conversion(mock_check, mock_rate, mock_uow):
	"""Перевод с конвертацией валют (RUB -> USD)."""
	user_id = uuid4()
	from_id, to_id = uuid4(), uuid4()

	mock_from = MagicMock(spec=models.BankAccount)
	mock_from.currency, mock_from.balance = "RUB", Decimal("10000")
	mock_from.client_id, mock_from.status = user_id, "open"

	mock_to = MagicMock(spec=models.BankAccount)
	mock_to.currency, mock_to.balance = "USD", Decimal("0")
	mock_to.status = "open"

	mock_uow.transactions.lock_accounts.return_value = {from_id: mock_from, to_id: mock_to}
	mock_uow.transactions.get_owner_contact.return_value = MagicMock(email="sender@test.com")
	mock_check.return_value = (True, [])
	# Курс RUB -> USD = 0.01 (100 руб = 1 доллар)
	mock_rate.return_value = Decimal("0.01")

	await transfer(mock_uow, user_id, from_id, to_id, Decimal("1000"), "Conversion")

	assert mock_from.balance == Decimal("9000")
	assert mock_to.balance == Decimal("10.00")  # 1000 * 0.01
	mock_rate.assert_awaited_once_with("RUB", "USD")


@pytest.mark.asyncio
async def test_transfer_same_account(mock_uow):
	"""Ошибка: перевод самому себе на тот же счет."""
	user_id = uuid4()
	acc_id = uuid4()

	from transaction_service.core.exceptions import SameAccountTransfer

	with pytest.raises(SameAccountTransfer):
		await transfer(mock_uow, user_id, acc_id, acc_id, Decimal("100"), "self")
