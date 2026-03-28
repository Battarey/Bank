import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from decimal import Decimal

from datetime import datetime, timezone
from transaction_service.deposit.router import deposit
from transaction_service.exceptions import AccountNotFound, AccountNotOpen, TransactionConflict
from shared.schemas import DepositRequest
from shared import models


def _make_tx():
    tx = models.Transaction(
        id=uuid4(),
        account_id=uuid4(),
        type="deposit",
        amount=Decimal("500"),
        created_at=datetime.now(timezone.utc),
        description=None,
        related_account_id=None,
        direction="incoming",
        status="posted",
        balance_before=Decimal("1000"),
        balance_after=Decimal("1500"),
        external_ref=None,
    )
    return tx


@pytest.mark.asyncio
@patch("transaction_service.deposit.router.service.deposit")
async def test_deposit_router_success(mock_svc):
    """Успешный вызов эндпоинта → 200."""
    mock_svc.return_value = _make_tx()

    session = AsyncMock()
    user_id = uuid4()
    account_id = uuid4()
    payload = DepositRequest.model_validate({"amount": "500.00", "description": "тест"})

    res = await deposit(account_id=account_id, payload=payload, user_id=user_id, session=session)
    assert "Счёт успешно пополнен" in res.message


@pytest.mark.asyncio
@patch("transaction_service.deposit.router.service.deposit")
async def test_deposit_router_not_found(mock_svc):
    """AccountNotFound → 404."""
    from fastapi import HTTPException
    mock_svc.side_effect = AccountNotFound("нет")
    session = AsyncMock()
    payload = DepositRequest.model_validate({"amount": "500.00"})

    with pytest.raises(HTTPException) as exc:
        await deposit(account_id=uuid4(), payload=payload, user_id=uuid4(), session=session)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
@patch("transaction_service.deposit.router.service.deposit")
async def test_deposit_router_conflict(mock_svc):
    """TransactionConflict → 409."""
    from fastapi import HTTPException
    mock_svc.side_effect = TransactionConflict("конфликт")
    session = AsyncMock()
    payload = DepositRequest.model_validate({"amount": "500.00"})

    with pytest.raises(HTTPException) as exc:
        await deposit(account_id=uuid4(), payload=payload, user_id=uuid4(), session=session)
    assert exc.value.status_code == 409
