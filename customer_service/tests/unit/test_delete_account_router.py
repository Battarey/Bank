import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import HTTPException

from customer_service.delete_account import service
from customer_service.delete_account.router import delete_account

@pytest.mark.asyncio
@patch("customer_service.delete_account.router.service.delete_account")
async def test_delete_account_success(mock_svc_delete):
    session = AsyncMock()
    user_id = uuid4()
    
    result = await delete_account(user_id=user_id, session=session)
    assert result.message == "Аккаунт успешно удалён."
    mock_svc_delete.assert_awaited_once_with(session, user_id)

@pytest.mark.asyncio
@patch("customer_service.delete_account.router.service.delete_account")
async def test_delete_account_not_found(mock_svc_delete):
    session = AsyncMock()
    user_id = uuid4()
    mock_svc_delete.side_effect = service.DeleteAccountNotFound("Not found")
    
    with pytest.raises(HTTPException) as exc:
        await delete_account(user_id=user_id, session=session)
    
    assert exc.value.status_code == 404
    assert exc.value.detail == "Not found"

@pytest.mark.asyncio
@patch("customer_service.delete_account.router.service.delete_account")
async def test_delete_account_already_deleted(mock_svc_delete):
    session = AsyncMock()
    user_id = uuid4()
    mock_svc_delete.side_effect = service.DeleteAccountAlreadyDeleted("Already")
    
    with pytest.raises(HTTPException) as exc:
        await delete_account(user_id=user_id, session=session)
    
    assert exc.value.status_code == 409
    assert exc.value.detail == "Already"
