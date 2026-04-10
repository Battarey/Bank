from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest

from account_service.exceptions import (
    AccountAlreadyFrozen,
    UnfreezeNotAllowed,
)
from account_service.freeze_account.router import resume_account, suspend_account
from shared import models


@pytest.mark.asyncio
@patch("account_service.freeze_account.router.service.freeze_account")
async def test_freeze_success(mock_svc, uow):
    user_id = uuid4()
    account_id = uuid4()
    
    # Mocking the account object
    account = models.BankAccount(
        id=account_id,
        account_number="123",
        type="checking",
        currency="RUB",
        balance=Decimal("0"),
        status="frozen",
        client_id=user_id,
        opened_at=datetime.now(UTC)
    )
    
    mock_svc.return_value = account
    
    res = await suspend_account(account_id, user_id, uow)
    assert res.message == "Обслуживание счёта приостановлено."
    assert res.account.status == "frozen"


@pytest.mark.asyncio
@patch("account_service.freeze_account.router.service.freeze_account")
async def test_freeze_error(mock_svc, uow):
    user_id = uuid4()
    account_id = uuid4()
    mock_svc.side_effect = AccountAlreadyFrozen("x")
    
    with pytest.raises(AccountAlreadyFrozen) as exc:
        await suspend_account(account_id, user_id, uow)
    assert "x" in str(exc.value)


@pytest.mark.asyncio
@patch("account_service.freeze_account.router.service.unfreeze_account")
async def test_unfreeze_success(mock_svc, uow):
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
        opened_at=datetime.now(UTC)
    )
    
    mock_svc.return_value = account
    
    res = await resume_account(account_id, user_id, uow)
    assert res.message == "Обслуживание счёта возобновлено."
    assert res.account.status == "open"


@pytest.mark.asyncio
@patch("account_service.freeze_account.router.service.unfreeze_account")
async def test_unfreeze_error(mock_svc, uow):
    user_id = uuid4()
    account_id = uuid4()
    mock_svc.side_effect = UnfreezeNotAllowed("x")
    
    with pytest.raises(UnfreezeNotAllowed) as exc:
        await resume_account(account_id, user_id, uow)
    assert "x" in str(exc.value)
