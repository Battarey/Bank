import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from unittest.mock import AsyncMock, MagicMock

from account_service.close_account.service import close_account
from account_service.exceptions import (
    AccountConflict,
    AccountNonZeroBalance,
    AccountNotOpen,
)
from shared import models
from shared.events.base import NotificationEvent, LogEvent

# --- Тесты ---

@pytest.mark.asyncio
async def test_close_account_not_open(uow):
    """Проверка ошибки при попытке закрыть уже замороженный или закрытый счет."""
    user_id = uuid4()
    acc = models.BankAccount(client_id=user_id, status="frozen")
    uow.accounts.get_by_user.return_value = acc
    
    with pytest.raises(AccountNotOpen):
        await close_account(uow, user_id, uuid4())

@pytest.mark.asyncio
async def test_close_account_nonzero_balance(uow):
    """Проверка ошибки при попытке закрыть счет с ненулевым остатком."""
    user_id = uuid4()
    acc = models.BankAccount(client_id=user_id, status="open", balance=Decimal("100.00"), currency="RUB")
    uow.accounts.get_by_user.return_value = acc
    
    with pytest.raises(AccountNonZeroBalance):
        await close_account(uow, user_id, uuid4())

@pytest.mark.asyncio
async def test_close_account_success(uow):
    """Успешный сценарий закрытия счета с регистрацией всех событий."""
    user_id = uuid4()
    acc = models.BankAccount(
        id=uuid4(), 
        client_id=user_id, 
        status="open", 
        balance=Decimal("0.00"), 
        account_number="12345678901234567890"
    )
    uow.accounts.get_by_user.return_value = acc
    uow.accounts.get_owner_contact.return_value = models.Contact(email="test@test.com")
    
    res = await close_account(uow, user_id, acc.id)
    
    assert res.status == "closed"
    assert res.closed_at is not None
    assert uow.committed is True
    
    # Проверка регистрации событий в UoW
    notifications = [e for e in uow.events if isinstance(e, NotificationEvent)]
    logs = [e for e in uow.events if isinstance(e, LogEvent)]
    
    assert len(notifications) == 1
    assert notifications[0].type == "account_closed"
    assert notifications[0].to == "test@test.com"
    
    assert len(logs) == 1
    assert logs[0].action == "close_account"
    
    uow.accounts.refresh.assert_awaited_once_with(acc)

@pytest.mark.asyncio
async def test_close_account_integrity_error(uow):
    """Проверка корректного отката (rollback) при ошибке целостности в БД."""
    user_id = uuid4()
    acc = models.BankAccount(id=uuid4(), client_id=user_id, status="open", balance=Decimal("0.00"))
    uow.accounts.get_by_user.return_value = acc
    uow.accounts.get_owner_contact.return_value = None
    
    # Имитируем ошибку IntegrityError при вызове commit
    uow.commit = AsyncMock(side_effect=IntegrityError("stmt", {}, Exception()))
    
    with pytest.raises(AccountConflict):
        await close_account(uow, user_id, acc.id)
    
    assert uow.rolled_back is True
