import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timezone

from transaction_service.withdrawal.router import withdraw
from transaction_service.exceptions import (
    AccountNotFound, AccountFrozen, InsufficientFunds,
    AccountNotOpen, SecurityViolation, TransactionConflict
)
from shared import schemas, models


def _make_payload():
    return schemas.WithdrawalRequest.model_validate({"amount": "100.00"})


def _make_tx():
    tx = models.Transaction(
        id=uuid4(), account_id=uuid4(), type="withdrawal",
        amount=Decimal("100"), created_at=datetime.now(timezone.utc),
        description=None, related_account_id=None, direction="outgoing",
        status="posted", balance_before=Decimal("1000"),
        balance_after=Decimal("900"), external_ref=None,
    )
    return tx


@pytest.mark.asyncio
@patch("transaction_service.withdrawal.router.service.withdraw")
async def test_withdraw_router_success(mock_svc):
    mock_svc.return_value = _make_tx()
    session = AsyncMock()

    res = await withdraw(account_id=uuid4(), payload=_make_payload(), user_id=uuid4(), session=session)
    assert "Средства успешно списаны" in res.message


@pytest.mark.asyncio
@patch("transaction_service.withdrawal.router.service.withdraw")
async def test_withdraw_router_not_found(mock_svc):
    from fastapi import HTTPException
    mock_svc.side_effect = AccountNotFound("нет")
    with pytest.raises(HTTPException) as exc:
        await withdraw(account_id=uuid4(), payload=_make_payload(), user_id=uuid4(), session=AsyncMock())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
@patch("transaction_service.withdrawal.router.service.withdraw")
async def test_withdraw_router_frozen(mock_svc):
    from fastapi import HTTPException
    mock_svc.side_effect = AccountFrozen("заморожен")
    with pytest.raises(HTTPException) as exc:
        await withdraw(account_id=uuid4(), payload=_make_payload(), user_id=uuid4(), session=AsyncMock())
    assert exc.value.status_code == 403


@pytest.mark.asyncio
@patch("transaction_service.withdrawal.router.service.withdraw")
async def test_withdraw_router_insufficient(mock_svc):
    from fastapi import HTTPException
    mock_svc.side_effect = InsufficientFunds("мало")
    with pytest.raises(HTTPException) as exc:
        await withdraw(account_id=uuid4(), payload=_make_payload(), user_id=uuid4(), session=AsyncMock())
    assert exc.value.status_code == 422


@pytest.mark.asyncio
@patch("transaction_service.withdrawal.router.service.withdraw")
async def test_withdraw_router_security(mock_svc):
    from fastapi import HTTPException
    mock_svc.side_effect = SecurityViolation("aml")
    with pytest.raises(HTTPException) as exc:
        await withdraw(account_id=uuid4(), payload=_make_payload(), user_id=uuid4(), session=AsyncMock())
    assert exc.value.status_code == 403
