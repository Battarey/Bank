import pytest
from uuid import uuid4
from unittest.mock import patch, MagicMock, AsyncMock
from transaction_service.history.router import list_transactions


@pytest.mark.asyncio
@patch("transaction_service.history.router.service.list_transactions")
async def test_list_transactions_router_success(mock_svc, mock_uow):
    """Роутер: успешное получение списка историй."""
    user_id = uuid4()
    account_id = uuid4()
    
    mock_svc.return_value = ([], 0)
    
    res = await list_transactions(
        account_id=account_id,
        limit=20,
        offset=0,
        user_id=user_id,
        uow=mock_uow
    )
    
    assert res.total == 0
    assert len(res.transactions) == 0
    mock_svc.assert_awaited_once()
