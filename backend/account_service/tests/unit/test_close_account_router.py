from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest

from account_service.close_account.router import close_account
from account_service.exceptions import (
    AccountNonZeroBalance,
)
from shared import models


@pytest.mark.asyncio
@patch("account_service.close_account.router.service.close_account")
async def test_close_account_success(mock_svc, uow):
    user_id = uuid4()
    account_id = uuid4()
    
    # Mocking the account object
    account = models.BankAccount(
        id=account_id,
        account_number="123",
        type="checking",
        currency="RUB",
        balance=Decimal("0"),
        status="closed",
        client_id=user_id,
        opened_at=datetime.now(UTC)
    )
    
    mock_svc.return_value = account
    
    res = await close_account(account_id, user_id, uow)
    assert res.message == "Счёт успешно закрыт."
    assert res.account.status == "closed"


@pytest.mark.asyncio
@patch("account_service.close_account.router.service.close_account")
async def test_close_account_error(mock_svc, uow):
    user_id = uuid4()
    account_id = uuid4()
    
    mock_svc.side_effect = AccountNonZeroBalance("x")
    
    with pytest.raises(AccountNonZeroBalance) as exc:
        await close_account(account_id, user_id, uow)
    assert "x" in str(exc.value)
