import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timezone

from transaction_service.transfer.router import transfer
from transaction_service.exceptions import (
    AccountNotFound, AccountFrozen, InsufficientFunds,
    SameAccountTransfer, SecurityViolation, RateUnavailable, TransactionConflict
)
from shared import schemas, models


def _make_transfer_payload():
    return schemas.TransferRequest.model_validate({
        "to_account_id": str(uuid4()),
        "amount": "100.00",
    })


def _make_tx():
    tx = models.Transaction(
        id=uuid4(), account_id=uuid4(), type="transfer",
        amount=Decimal("100"), created_at=datetime.now(timezone.utc),
        description=None, related_account_id=None, direction="outgoing",
        status="posted", balance_before=Decimal("1000"),
        balance_after=Decimal("900"), external_ref=None,
    )
    return tx


@pytest.mark.asyncio
@patch("transaction_service.transfer.router.service.transfer")
async def test_transfer_router_success(mock_svc):
    mock_svc.return_value = _make_tx()
    res = await transfer(account_id=uuid4(), payload=_make_transfer_payload(), user_id=uuid4(), session=AsyncMock())
    assert "Перевод выполнен" in res.message


@pytest.mark.asyncio
@patch("transaction_service.transfer.router.service.transfer")
async def test_transfer_router_not_found(mock_svc):
    from fastapi import HTTPException
    mock_svc.side_effect = AccountNotFound("нет")
    with pytest.raises(HTTPException) as exc:
        await transfer(account_id=uuid4(), payload=_make_transfer_payload(), user_id=uuid4(), session=AsyncMock())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
@patch("transaction_service.transfer.router.service.transfer")
async def test_transfer_router_frozen(mock_svc):
    from fastapi import HTTPException
    mock_svc.side_effect = AccountFrozen("заморожен")
    with pytest.raises(HTTPException) as exc:
        await transfer(account_id=uuid4(), payload=_make_transfer_payload(), user_id=uuid4(), session=AsyncMock())
    assert exc.value.status_code == 403


@pytest.mark.asyncio
@patch("transaction_service.transfer.router.service.transfer")
async def test_transfer_router_rate_unavail(mock_svc):
    from fastapi import HTTPException
    mock_svc.side_effect = RateUnavailable("курс недоступен")
    with pytest.raises(HTTPException) as exc:
        await transfer(account_id=uuid4(), payload=_make_transfer_payload(), user_id=uuid4(), session=AsyncMock())
    assert exc.value.status_code == 502


@pytest.mark.asyncio
@patch("transaction_service.transfer.router.service.transfer")
async def test_transfer_router_same_account(mock_svc):
    from fastapi import HTTPException
    mock_svc.side_effect = SameAccountTransfer("тот же счёт")
    with pytest.raises(HTTPException) as exc:
        await transfer(account_id=uuid4(), payload=_make_transfer_payload(), user_id=uuid4(), session=AsyncMock())
    assert exc.value.status_code == 409
