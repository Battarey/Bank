import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import HTTPException
from decimal import Decimal
from datetime import datetime, UTC

from account_service.freeze_account.router import suspend_account, resume_account
from account_service.exceptions import (
    AccountAlreadyFrozen,
    AccountError,
    AccountNotFound,
    AccountNotFrozen,
    AccountNotOpen,
    UnfreezeNotAllowed,
)
from shared import models


@pytest.mark.asyncio
@patch("account_service.freeze_account.router.service.freeze_account")
async def test_freeze_success(mock_svc):
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
    account.status = "frozen"
    account.client_id = user_id
    account.opened_at = datetime.now(UTC)
    
    mock_svc.return_value = account
    
    res = await suspend_account(account_id, user_id, session)
    assert res.message == "Обслуживание счёта приостановлено."
    assert res.account.status == "frozen"


@pytest.mark.asyncio
@patch("account_service.freeze_account.router.service.freeze_account")
async def test_freeze_error(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    account_id = uuid4()
    mock_svc.side_effect = AccountAlreadyFrozen("x")
    
    with pytest.raises(AccountAlreadyFrozen) as exc:
        await suspend_account(account_id, user_id, session)
    assert "x" in str(exc.value)


@pytest.mark.asyncio
@patch("account_service.freeze_account.router.service.unfreeze_account")
async def test_unfreeze_success(mock_svc):
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
    
    res = await resume_account(account_id, user_id, session)
    assert res.message == "Обслуживание счёта возобновлено."
    assert res.account.status == "open"


@pytest.mark.asyncio
@patch("account_service.freeze_account.router.service.unfreeze_account")
async def test_unfreeze_error(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    account_id = uuid4()
    mock_svc.side_effect = UnfreezeNotAllowed("x")
    
    with pytest.raises(UnfreezeNotAllowed) as exc:
        await resume_account(account_id, user_id, session)
    assert "x" in str(exc.value)
