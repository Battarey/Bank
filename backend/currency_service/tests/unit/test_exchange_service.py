from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest

from currency_service.core.exceptions import (
	AccountNotFound,
	AccountNotOpen,
	InsufficientFunds,
	RateUnavailable,
	SameAccountExchange,
	SameCurrencyExchange,
)
from currency_service.services.exchange import exchange
from shared import models


def _make_account(status="open", balance=Decimal("1000"), currency="RUB", client_id=None):
	acc = models.BankAccount()
	acc.id = uuid4()
	acc.client_id = client_id or uuid4()
	acc.status = status
	acc.balance = balance
	acc.currency = currency
	acc.account_number = "40817810000000000001"
	return acc


@pytest.fixture
def user_id():
	return uuid4()


@pytest.fixture
def accounts(user_id):
	from_acc = _make_account(currency="RUB", balance=Decimal("10000"), client_id=user_id)
	to_acc = _make_account(currency="USD", balance=Decimal("0"), client_id=user_id)
	return from_acc, to_acc


@pytest.mark.asyncio
async def test_exchange_same_account(uow):
	"""Ошибка: обмен на тот же самый счет."""
	acc_id = uuid4()
	with pytest.raises(SameAccountExchange):
		await exchange(uow, uuid4(), acc_id, acc_id, Decimal("100"))


@pytest.mark.asyncio
async def test_exchange_from_not_found(uow, user_id):
	"""Ошибка: счет списания не найден."""
	uow.accounts.lock_accounts.return_value = {}

	with pytest.raises(AccountNotFound, match="Счёт списания"):
		await exchange(uow, user_id, uuid4(), uuid4(), Decimal("100"))


@pytest.mark.asyncio
async def test_exchange_same_currency(uow, user_id, accounts):
	"""Ошибка: валюты счетов совпадают."""
	from_acc, to_acc = accounts
	to_acc.currency = "RUB"
	uow.accounts.lock_accounts.return_value = {from_acc.id: from_acc, to_acc.id: to_acc}

	with pytest.raises(SameCurrencyExchange):
		await exchange(uow, user_id, from_acc.id, to_acc.id, Decimal("100"))


@pytest.mark.asyncio
async def test_exchange_insufficient_funds(uow, user_id, accounts):
	"""Ошибка: недостаточно средств."""
	from_acc, to_acc = accounts
	from_acc.balance = Decimal("10")
	uow.accounts.lock_accounts.return_value = {from_acc.id: from_acc, to_acc.id: to_acc}

	with pytest.raises(InsufficientFunds):
		await exchange(uow, user_id, from_acc.id, to_acc.id, Decimal("100"))


@pytest.mark.asyncio
@patch("currency_service.services.exchange.exchange_client.get_fresh_rate")
async def test_exchange_success(mock_rate, uow, user_id, accounts):
	"""Успешный обмен валют с проверкой событий и проводок."""
	from_acc, to_acc = accounts
	uow.accounts.lock_accounts.return_value = {from_acc.id: from_acc, to_acc.id: to_acc}
	uow.accounts.get_owner_contact.return_value = models.Contact(email="test@test.com")
	mock_rate.return_value = (Decimal("0.011"), None)

	from_amount, to_amount, _rate = await exchange(uow, user_id, from_acc.id, to_acc.id, Decimal("1000"))

	assert from_amount == Decimal("1000")
	assert to_amount == Decimal("11.00")
	assert from_acc.balance == Decimal("9000")
	assert to_acc.balance == Decimal("11.00")

	# Проверка вызова репозитория
	uow.accounts.add_all.assert_called_once()
	assert uow.committed is True

	# Проверка регистрации событий
	assert any(e.type == "transaction_transfer" for e in uow.events)
	assert any(getattr(e, "action", None) == "currency_exchange" for e in uow.events)


@pytest.mark.asyncio
@patch("currency_service.services.exchange.exchange_client.get_fresh_rate")
async def test_exchange_rate_unavailable(mock_rate, uow, user_id, accounts):
	"""Ошибка: курс валют недоступен."""
	from_acc, to_acc = accounts
	uow.accounts.lock_accounts.return_value = {from_acc.id: from_acc, to_acc.id: to_acc}
	mock_rate.side_effect = Exception("API timeout")

	with pytest.raises(RateUnavailable):
		await exchange(uow, user_id, from_acc.id, to_acc.id, Decimal("100"))


@pytest.mark.asyncio
async def test_exchange_not_open(uow, user_id, accounts):
	"""Ошибка: счет не является открытым (заморожен/закрыт)."""
	from_acc, to_acc = accounts
	from_acc.status = "frozen"
	uow.accounts.lock_accounts.return_value = {from_acc.id: from_acc, to_acc.id: to_acc}

	with pytest.raises(AccountNotOpen):
		await exchange(uow, user_id, from_acc.id, to_acc.id, Decimal("100"))
