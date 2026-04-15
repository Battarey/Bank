from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest

from account_service.core.exceptions import (
	AccountNotFound,
	AccountOwnerNotFound,
)
from account_service.api.accounts import get_account, list_accounts, open_account
from shared import models, schemas


@pytest.mark.asyncio
@patch("account_service.api.accounts.service.open_account")
async def test_open_account_success(mock_svc, uow):
	user_id = uuid4()
	payload = schemas.OpenAccountRequest(type="checking", currency="RUB")

	# Mocking the account object
	account = models.BankAccount(
		id=uuid4(),
		account_number="123",
		type="checking",
		currency="RUB",
		balance=Decimal("0"),
		status="open",
		client_id=user_id,
		opened_at=datetime.now(UTC),
	)

	mock_svc.return_value = account

	res = await open_account(payload, user_id, uow)
	assert res.message == "Счёт успешно открыт."
	assert res.account.account_number == "123"


@pytest.mark.asyncio
@patch("account_service.api.accounts.service.open_account")
async def test_open_account_error(mock_svc, uow):
	user_id = uuid4()
	payload = schemas.OpenAccountRequest(type="checking", currency="RUB")
	mock_svc.side_effect = AccountOwnerNotFound("x")

	with pytest.raises(AccountOwnerNotFound) as exc:
		await open_account(payload, user_id, uow)
	assert "x" in str(exc.value)


@pytest.mark.asyncio
@patch("account_service.api.accounts.service.list_accounts")
async def test_list_accounts_success(mock_svc, uow):
	user_id = uuid4()

	# Mocking the account object
	account = models.BankAccount(
		id=uuid4(),
		account_number="123",
		type="checking",
		currency="RUB",
		balance=Decimal("0"),
		status="open",
		client_id=user_id,
		opened_at=datetime.now(UTC),
	)

	mock_svc.return_value = ([account], 1)

	res = await list_accounts(user_id, uow)
	assert res.total == 1
	assert res.accounts[0].account_number == "123"


@pytest.mark.asyncio
@patch("account_service.api.accounts.service.get_account")
async def test_get_account_success(mock_svc, uow):
	user_id = uuid4()
	account_id = uuid4()

	# Mocking the account object
	account = models.BankAccount(
		id=account_id,
		account_number="123",
		type="checking",
		currency="RUB",
		balance=Decimal("0"),
		status="open",
		client_id=user_id,
		opened_at=datetime.now(UTC),
	)

	mock_svc.return_value = account

	res = await get_account(account_id, user_id, uow)
	assert res.account_number == "123"


@pytest.mark.asyncio
@patch("account_service.api.accounts.service.get_account")
async def test_get_account_error(mock_svc, uow):
	user_id = uuid4()
	account_id = uuid4()
	mock_svc.side_effect = AccountNotFound("x")

	with pytest.raises(AccountNotFound) as exc:
		await get_account(account_id, user_id, uow)
	assert "x" in str(exc.value)
