import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from customer_service.delete_account.service import (
    DeleteAccountAlreadyDeleted,
    DeleteAccountNotFound,
    delete_account,
)
from shared import models

@pytest.fixture
def mock_session():
    return AsyncMock()

@pytest.mark.asyncio
async def test_delete_account_not_found(mock_session):
    mock_session.get.return_value = None
    with pytest.raises(DeleteAccountNotFound):
        await delete_account(mock_session, uuid4())

@pytest.mark.asyncio
async def test_delete_account_already_deleted(mock_session):
    user = models.User(status="deleted")
    mock_session.get.return_value = user
    with pytest.raises(DeleteAccountAlreadyDeleted):
        await delete_account(mock_session, uuid4())

@pytest.mark.asyncio
@patch("customer_service.delete_account.service.publish")
async def test_delete_account_success(mock_publish, mock_session):
    user_id = uuid4()
    user = models.User(id=user_id, status="active")
    
    acc1 = models.BankAccount(id=uuid4(), status="open")
    acc2 = models.BankAccount(id=uuid4(), status="open")
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [acc1, acc2]
    mock_session.execute.return_value = mock_result
    
    contact = models.Contact(email="test@example.com")
    def get_side_effect(model, pk):
        if model == models.User:
            return user
        if model == models.Contact:
            return contact
        return None
    mock_session.get.side_effect = get_side_effect
    
    await delete_account(mock_session, user_id)
    
    assert user.status == "deleted"
    assert acc1.status == "frozen"
    assert acc1.frozen_by == "system"
    assert acc2.status == "frozen"
    
    assert mock_publish.call_count == 2
    mock_session.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_delete_account_commit_error(mock_session):
    user = models.User(status="active")
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    mock_session.get.return_value = user
    mock_session.commit.side_effect = Exception("DB error")
    
    with pytest.raises(Exception, match="DB error"):
        await delete_account(mock_session, uuid4())
    
    mock_session.rollback.assert_awaited_once()

@pytest.mark.asyncio
@patch("customer_service.delete_account.service.publish")
async def test_delete_account_publish_error(mock_publish, mock_session):
    user = models.User(id=uuid4(), status="active")
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    mock_session.get.side_effect = [user, models.Contact(email="x")]
    
    mock_publish.side_effect = Exception("RabbitMQ offline")
    
    await delete_account(mock_session, user.id)
    assert user.status == "deleted"
    mock_session.commit.assert_awaited_once()
