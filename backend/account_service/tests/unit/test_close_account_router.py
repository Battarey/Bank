import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from decimal import Decimal
from fastapi import HTTPException
from datetime import datetime, UTC

from account_service.close_account.router import _raise, close_account
from account_service.exceptions import (
    AccountConflict,
    AccountError,
    AccountNonZeroBalance,
    AccountNotFound,
    AccountNotOpen,
)
from shared import models


def test_raise_exceptions():
    with pytest.raises(HTTPException) as exc:
        _raise(AccountNotFound("x"))
    assert exc.value.status_code == 404
    
    with pytest.raises(HTTPException) as exc:
        _raise(AccountNotOpen("x"))
    assert exc.value.status_code == 409
    
    with pytest.raises(HTTPException) as exc:
        _raise(AccountNonZeroBalance("x"))
    assert exc.value.status_code == 409
    
    with pytest.raises(HTTPException) as exc:
        _raise(AccountConflict("x"))
    assert exc.value.status_code == 409
    
    with pytest.raises(HTTPException) as exc:
        _raise(AccountError("x"))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
@patch("account_service.close_account.router.service.close_account")
async def test_close_account_success(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    account_id = uuid4()
    
    mock_svc.return_value = models.BankAccount(
        id=account_id, account_number="123", type="checking", currency="RUB", balance=Decimal("0"), status="closed", client_id=user_id, opened_at=datetime.now(UTC)
    )
    
    res = await close_account(account_id, user_id, session)
    assert res.message == "Счёт успешно закрыт."
    assert res.account.status == "closed"

@pytest.mark.asyncio
@patch("account_service.close_account.router.service.close_account")
async def test_close_account_error(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    account_id = uuid4()
    
    mock_svc.side_effect = AccountNonZeroBalance("x")
    
    with pytest.raises(HTTPException) as exc:
        await close_account(account_id, user_id, session)
    assert exc.value.status_code == 409
