from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import HTTPException
from datetime import datetime, UTC

from account_service.open_account.router import _raise, open_account, list_accounts, get_account
from account_service.exceptions import (
    AccountConflict,
    AccountError,
    AccountLimitReached,
    AccountNotFound,
    AccountOwnerNotFound,
)
from shared import schemas, models


def test_raise_exceptions():
    with pytest.raises(HTTPException) as exc:
        _raise(AccountNotFound("x"))
    assert exc.value.status_code == 404
    
    with pytest.raises(HTTPException) as exc:
        _raise(AccountOwnerNotFound("x"))
    assert exc.value.status_code == 404
    
    with pytest.raises(HTTPException) as exc:
        _raise(AccountLimitReached("x"))
    assert exc.value.status_code == 409
    
    with pytest.raises(HTTPException) as exc:
        _raise(AccountConflict("x"))
    assert exc.value.status_code == 409
    
    with pytest.raises(HTTPException) as exc:
        _raise(AccountError("x"))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
@patch("account_service.open_account.router.service.open_account")
async def test_open_account_success(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    payload = schemas.OpenAccountRequest(type="checking", currency="RUB")
    
    mock_svc.return_value = models.BankAccount(
        id=uuid4(), account_number="123", type="checking", currency="RUB", balance=Decimal("0"), status="open", client_id=user_id, opened_at=datetime.now(UTC)
    )
    
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
    
    with pytest.raises(HTTPException) as exc:
        await open_account(payload, user_id, session)
    assert exc.value.status_code == 404

@pytest.mark.asyncio
@patch("account_service.open_account.router.service.list_accounts")
async def test_list_accounts_success(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    
    acc = models.BankAccount(id=uuid4(), account_number="123", type="checking", currency="RUB", balance=Decimal("0"), status="open", client_id=user_id, opened_at=datetime.now(UTC))
    mock_svc.return_value = [acc]
    
    res = await list_accounts(user_id, session)
    assert res.total == 1
    assert res.accounts[0].account_number == "123"

@pytest.mark.asyncio
@patch("account_service.open_account.router.service.get_account")
async def test_get_account_success(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    account_id = uuid4()
    
    acc = models.BankAccount(id=uuid4(), account_number="123", type="checking", currency="RUB", balance=Decimal("0"), status="open", client_id=user_id, opened_at=datetime.now(UTC))
    mock_svc.return_value = acc
    
    res = await get_account(account_id, user_id, session)
    assert res.account_number == "123"

@pytest.mark.asyncio
@patch("account_service.open_account.router.service.get_account")
async def test_get_account_error(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    account_id = uuid4()
    mock_svc.side_effect = AccountNotFound("x")
    
    with pytest.raises(HTTPException) as exc:
        await get_account(account_id, user_id, session)
    assert exc.value.status_code == 404
