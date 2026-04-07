import pytest
from uuid import uuid4
from unittest.mock import AsyncMock

from customer_service.delete_account.service import delete_account
from customer_service.exceptions import AccountNotFound, AccountAlreadyDeleted
from shared import models


@pytest.mark.asyncio
async def test_delete_account_not_found(uow):
    """Пользователь не найден."""
    uow.customers.get.return_value = None
    
    with pytest.raises(AccountNotFound):
        await delete_account(uow, uuid4())


@pytest.mark.asyncio
async def test_delete_account_already_deleted(uow):
    """Пользователь уже удален."""
    user = models.User(status="deleted")
    uow.customers.get.return_value = user
    
    with pytest.raises(AccountAlreadyDeleted):
        await delete_account(uow, uuid4())


@pytest.mark.asyncio
async def test_delete_account_success(uow):
    """Успешное мягкое удаление аккаунта."""
    user_id = uuid4()
    user = models.User(id=user_id, status="active")
    uow.customers.get.return_value = user
    
    acc1 = models.BankAccount(id=uuid4(), status="open")
    uow.customers.get_open_accounts.return_value = [acc1]
    uow.customers.get_contact.return_value = models.Contact(email="test@test.com")
    
    await delete_account(uow, user_id)
    
    assert user.status == "deleted"
    assert acc1.status == "frozen"
    assert uow.committed is True
    assert len(uow.events) == 2
    assert uow.events[1].action == "delete_account"


@pytest.mark.asyncio
async def test_delete_account_rollback_on_error(uow):
    """Откат транзакции при ошибке коммита."""
    user_id = uuid4()
    uow.customers.get.return_value = models.User(id=user_id, status="active")
    uow.customers.get_open_accounts.return_value = []
    uow.customers.get_contact.return_value = None
    
    uow.commit = AsyncMock(side_effect=Exception("DB error"))
    
    with pytest.raises(Exception, match="DB error"):
        await delete_account(uow, user_id)
    
    assert uow.rolled_back is True
