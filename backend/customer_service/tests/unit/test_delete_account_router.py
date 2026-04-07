import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from customer_service.delete_account.router import delete_account


@pytest.mark.asyncio
@patch("customer_service.delete_account.router.service.delete_account", new_callable=AsyncMock)
async def test_router_delete_account(mock_svc, uow):
    """Роутер: мягкое удаление аккаунта."""
    user_id = uuid4()
    
    res = await delete_account(user_id=user_id, uow=uow)
    
    assert "успешно удалён" in res.message
    mock_svc.assert_awaited_once_with(uow, user_id)
