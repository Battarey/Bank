from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import HTTPException
from datetime import datetime, UTC

from account_service.open_account.router import open_account, list_accounts, get_account
from account_service.exceptions import (
    AccountConflict,
    AccountError,
    AccountLimitReached,
    AccountNotFound,
    AccountOwnerNotFound,
)
from shared import schemas, models


@pytest.mark.asyncio
@patch("account_service.open_account.router.service.open_account")
async def test_open_account_success(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    payload = schemas.OpenAccountRequest(type="checking", currency="RUB")
    
    # Mocking the account object
    account = models.BankAccount()
    account.id = uuid4()
    account.account_number = "123"
    account.type = "checking"
    account.currency = "RUB"
    account.balance = Decimal("0")
    account.status = "open"
    account.client_id = user_id
    account.opened_at = datetime.now(UTC)
    
    mock_svc.return_value = account
    
    res = await open_account(payload, user_id, session)
    assert res.message == "Счёт успешно открыт."
    assert res.account.account_number == "123"


@pytest.mark.asyncio
@patch("account_service.open_account.router.service.open_account")
async def test_open_account_error(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    payload = schemas.OpenAccountRequest(type="checking", currency="RUB")
    mock_svc.side_effect = AccountOwnerNotFound("x")
    
    with pytest.raises(AccountOwnerNotFound) as exc:
        await open_account(payload, user_id, session)
    assert "x" in str(exc.value)


@pytest.mark.asyncio
@patch("account_service.open_account.router.service.list_accounts")
async def test_list_accounts_success(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    
    # Mocking the account object
    account = models.BankAccount()
    account.id = uuid4()
    account.account_number = "123"
    account.type = "checking"
    account.currency = "RUB"
    account.balance = Decimal("0")
    account.status = "open"
    account.client_id = user_id
    account.opened_at = datetime.now(UTC)
    
    mock_svc.return_value = [account]
    
    res = await list_accounts(user_id, session)
    assert res.total == 1
    assert res.accounts[0].account_number == "123"


@pytest.mark.asyncio
@patch("account_service.open_account.router.service.get_account")
async def test_get_account_success(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    account_id = uuid4()
    
    # Mocking the account object
    account = models.BankAccount()
    account.id = account_id
    account.account_number = "123"
    account.type = "checking"
    account.currency = "RUB"
    account.balance = Decimal("0")
    account.status = "open"
    account.client_id = user_id
    account.opened_at = datetime.now(UTC)
    
    mock_svc.return_value = account
    
    res = await get_account(account_id, user_id, session)
    assert res.account_number == "123"


@pytest.mark.asyncio
@patch("account_service.open_account.router.service.get_account")
async def test_get_account_error(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    account_id = uuid4()
    mock_svc.side_effect = AccountNotFound("x")
    
    with pytest.raises(AccountNotFound) as exc:
        await get_account(account_id, user_id, session)
    assert "x" in str(exc.value)
