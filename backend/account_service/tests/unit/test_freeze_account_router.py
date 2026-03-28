import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import HTTPException
from decimal import Decimal
from datetime import datetime, UTC

from account_service.freeze_account.router import _raise, freeze, unfreeze
from account_service.exceptions import (
    AccountAlreadyFrozen,
    AccountError,
    AccountNotFound,
    AccountNotFrozen,
    AccountNotOpen,
    UnfreezeNotAllowed,
)
from shared import models

def test_raise_exceptions():
    with pytest.raises(HTTPException) as exc:
        _raise(AccountNotFound("x"))
    assert exc.value.status_code == 404
    
    with pytest.raises(HTTPException) as exc:
        _raise(AccountAlreadyFrozen("x"))
    assert exc.value.status_code == 409
    
    with pytest.raises(HTTPException) as exc:
        _raise(AccountNotFrozen("x"))
    assert exc.value.status_code == 409
    
    with pytest.raises(HTTPException) as exc:
        _raise(UnfreezeNotAllowed("x"))
    assert exc.value.status_code == 403
    
    with pytest.raises(HTTPException) as exc:
        _raise(AccountNotOpen("x"))
    assert exc.value.status_code == 409
    
    with pytest.raises(HTTPException) as exc:
        _raise(AccountError("x"))
    assert exc.value.status_code == 400

@pytest.mark.asyncio
@patch("account_service.freeze_account.router.service.freeze_account")
async def test_freeze_success(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    account_id = uuid4()
    
    mock_svc.return_value = models.BankAccount(
        id=account_id, account_number="123", type="checking", currency="RUB", balance=Decimal("0"), status="frozen", client_id=user_id, opened_at=datetime.now(UTC)
    )
    
    res = await freeze(account_id, user_id, session)
    assert res.message == "Счёт заморожен."
    assert res.account.status == "frozen"

@pytest.mark.asyncio
@patch("account_service.freeze_account.router.service.freeze_account")
async def test_freeze_error(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    account_id = uuid4()
    mock_svc.side_effect = AccountAlreadyFrozen("x")
    
    with pytest.raises(HTTPException) as exc:
        await freeze(account_id, user_id, session)
    assert exc.value.status_code == 409

@pytest.mark.asyncio
@patch("account_service.freeze_account.router.service.unfreeze_account")
async def test_unfreeze_success(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    account_id = uuid4()
    
    mock_svc.return_value = models.BankAccount(
        id=account_id, account_number="123", type="checking", currency="RUB", balance=Decimal("0"), status="open", client_id=user_id, opened_at=datetime.now(UTC)
    )
    
    res = await unfreeze(account_id, user_id, session)
    assert res.message == "Счёт разморожен."
    assert res.account.status == "open"

@pytest.mark.asyncio
@patch("account_service.freeze_account.router.service.unfreeze_account")
async def test_unfreeze_error(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    account_id = uuid4()
    mock_svc.side_effect = UnfreezeNotAllowed("x")
    
    with pytest.raises(HTTPException) as exc:
        await unfreeze(account_id, user_id, session)
    assert exc.value.status_code == 403
