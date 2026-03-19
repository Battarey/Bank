import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from account_service.open_account.service import (
    _generate_account_number,
    _is_number_unique,
    _generate_unique_number,
    _notify_account_opened,
    open_account,
    list_accounts,
    get_account,
    MAX_ACCOUNTS_PER_TYPE_CURRENCY,
)
from account_service.exceptions import (
    AccountConflict,
    AccountError,
    AccountLimitReached,
    AccountNotFound,
    AccountOwnerNotFound,
)
from shared import models, schemas

def test_generate_account_number():
    num = _generate_account_number("checking", "RUB")
    assert num.startswith("40817810")
    assert len(num) == 20

@pytest.mark.asyncio
async def test_is_number_unique_true(mock_session):
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.execute.return_value = mock_result
    assert await _is_number_unique(mock_session, "123") is True

@pytest.mark.asyncio
async def test_is_number_unique_false(mock_session):
    mock_result = MagicMock()
    mock_result.first.return_value = ("some_id",)
    mock_session.execute.return_value = mock_result
    assert await _is_number_unique(mock_session, "123") is False

@pytest.mark.asyncio
@patch("account_service.open_account.service._is_number_unique")
async def test_generate_unique_number_success(mock_unique, mock_session):
    mock_unique.side_effect = [False, False, True]
    num = await _generate_unique_number(mock_session, "savings", "USD")
    assert num.startswith("42301840")
    assert mock_unique.call_count == 3

@pytest.mark.asyncio
@patch("account_service.open_account.service._is_number_unique")
async def test_generate_unique_number_fails(mock_unique, mock_session):
    mock_unique.return_value = False
    with pytest.raises(AccountError, match="Не удалось сгенерировать"):
        await _generate_unique_number(mock_session, "credit", "EUR")
    assert mock_unique.call_count == 10

@pytest.mark.asyncio
@patch("account_service.open_account.service.publish")
async def test_notify_account_opened_no_contact(mock_publish, mock_session):
    mock_session.get.return_value = None
    await _notify_account_opened(mock_session, uuid4(), models.BankAccount())
    mock_publish.assert_not_awaited()

@pytest.mark.asyncio
@patch("account_service.open_account.service.publish")
async def test_notify_account_opened_success(mock_publish, mock_session):
    contact = models.Contact(email="a@a.com")
    mock_session.get.return_value = contact
    acc = models.BankAccount(type="checking", currency="RUB", account_number="123")
    await _notify_account_opened(mock_session, uuid4(), acc)
    mock_publish.assert_awaited_once()

@pytest.mark.asyncio
async def test_open_account_user_not_found(mock_session):
    mock_session.get.return_value = None
    with pytest.raises(AccountOwnerNotFound):
        await open_account(mock_session, uuid4(), schemas.OpenAccountRequest(type="checking", currency="RUB"))

@pytest.mark.asyncio
async def test_open_account_user_not_active(mock_session):
    mock_session.get.return_value = models.User(status="frozen")
    with pytest.raises(AccountOwnerNotFound):
        await open_account(mock_session, uuid4(), schemas.OpenAccountRequest(type="checking", currency="RUB"))

@pytest.mark.asyncio
async def test_open_account_limit_reached(mock_session):
    user = models.User(status="active")
    mock_session.get.return_value = user
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [models.BankAccount()] * MAX_ACCOUNTS_PER_TYPE_CURRENCY
    mock_session.execute.return_value = mock_result
    
    with pytest.raises(AccountLimitReached):
        await open_account(mock_session, uuid4(), schemas.OpenAccountRequest(type="checking", currency="RUB"))

@pytest.mark.asyncio
@patch("account_service.open_account.service.publish")
@patch("account_service.open_account.service._generate_unique_number")
@patch("account_service.open_account.service._notify_account_opened")
async def test_open_account_success(mock_notify, mock_gen, mock_publish, mock_session):
    user = models.User(status="active")
    def get_se(m, pk):
        if m == models.User: return user
        return None
    mock_session.get.side_effect = get_se
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    mock_gen.return_value = "12345"
    
    payload = schemas.OpenAccountRequest(type="checking", currency="RUB")
    acc = await open_account(mock_session, uuid4(), payload)
    
    assert acc.type == "checking"
    assert acc.currency == "RUB"
    assert acc.account_number == "12345"
    assert acc.balance == Decimal("0.00")
    
    mock_session.add.assert_called_once_with(acc)
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(acc)
    mock_notify.assert_awaited_once()
    mock_publish.assert_awaited_once()

@pytest.mark.asyncio
@patch("account_service.open_account.service.publish")
@patch("account_service.open_account.service._generate_unique_number")
@patch("account_service.open_account.service._notify_account_opened")
async def test_open_account_integrity_error(mock_notify, mock_gen, mock_publish, mock_session):
    user = models.User(status="active")
    mock_session.get.side_effect = [user, None]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    mock_gen.return_value = "12345"
    
    mock_session.commit.side_effect = IntegrityError("a", "b", "c")
    
    with pytest.raises(AccountConflict):
        await open_account(mock_session, uuid4(), schemas.OpenAccountRequest(type="checking", currency="RUB"))
    
    mock_session.rollback.assert_awaited_once()

@pytest.mark.asyncio
@patch("account_service.open_account.service.publish")
@patch("account_service.open_account.service._generate_unique_number")
@patch("account_service.open_account.service._notify_account_opened")
async def test_open_account_publish_error(mock_notify, mock_gen, mock_publish, mock_session):
    user = models.User(status="active")
    mock_session.get.side_effect = [user, None]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    mock_gen.return_value = "12345"
    
    mock_publish.side_effect = Exception("failed to log")
    
    # Should not raise exception
    acc = await open_account(mock_session, uuid4(), schemas.OpenAccountRequest(type="checking", currency="RUB"))
    assert acc.account_number == "12345"

@pytest.mark.asyncio
async def test_list_accounts(mock_session):
    acc1 = models.BankAccount(id=uuid4())
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [acc1]
    mock_session.execute.return_value = mock_result
    
    res = await list_accounts(mock_session, uuid4())
    assert len(res) == 1
    assert res[0] == acc1

@pytest.mark.asyncio
async def test_get_account_not_found(mock_session):
    mock_session.get.return_value = None
    with pytest.raises(AccountNotFound):
        await get_account(mock_session, uuid4(), uuid4())

@pytest.mark.asyncio
async def test_get_account_wrong_owner(mock_session):
    mock_session.get.return_value = models.BankAccount(client_id=uuid4())
    with pytest.raises(AccountNotFound):
        await get_account(mock_session, uuid4(), uuid4())

@pytest.mark.asyncio
async def test_get_account_success(mock_session):
    user_id = uuid4()
    acc = models.BankAccount(client_id=user_id)
    mock_session.get.return_value = acc
    res = await get_account(mock_session, user_id, uuid4())
    assert res == acc
