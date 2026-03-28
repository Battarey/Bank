import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from transaction_service.history.router import list_transactions
from transaction_service.exceptions import AccountNotFound


@pytest.mark.asyncio
@patch("transaction_service.history.router.service.list_transactions")
async def test_history_router_success(mock_svc):
    mock_svc.return_value = ([], 0)
    res = await list_transactions(
        account_id=uuid4(),
        limit=20, offset=0,
        type=None, direction=None,
        user_id=uuid4(),
        session=AsyncMock()
    )
    assert res.total == 0
    assert res.limit == 20


@pytest.mark.asyncio
@patch("transaction_service.history.router.service.list_transactions")
async def test_history_router_not_found(mock_svc):
    from fastapi import HTTPException
    mock_svc.side_effect = AccountNotFound("нет")
    with pytest.raises(HTTPException) as exc:
        await list_transactions(
            account_id=uuid4(),
            limit=20, offset=0,
            type=None, direction=None,
            user_id=uuid4(),
            session=AsyncMock()
        )
    assert exc.value.status_code == 404
