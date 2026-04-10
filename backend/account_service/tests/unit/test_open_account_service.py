from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from account_service.exceptions import (
	AccountLimitReached,
	AccountNotFound,
	AccountOwnerNotFound,
)
from account_service.open_account.service import (
	MAX_ACCOUNTS_PER_TYPE_CURRENCY,
	get_account,
	list_accounts,
	open_account,
)
from shared import models, schemas
from shared.events.base import LogEvent, NotificationEvent

# --- Тесты open_account ---


@pytest.mark.asyncio
async def test_open_account_user_not_active(uow):
	"""Проверка ошибки, если пользователь не найден или не активен."""
	uow.accounts.get_active_owner.side_effect = AccountOwnerNotFound("Not active")

	with pytest.raises(AccountOwnerNotFound):
		await open_account(uow, uuid4(), schemas.OpenAccountRequest(type="checking", currency="RUB"))


@pytest.mark.asyncio
async def test_open_account_limit_reached(uow):
	"""Проверка лимита на количество открытых счетов одного типа."""
	uow.accounts.count_open_by_type.return_value = MAX_ACCOUNTS_PER_TYPE_CURRENCY

	with pytest.raises(AccountLimitReached):
		await open_account(uow, uuid4(), schemas.OpenAccountRequest(type="checking", currency="RUB"))


@pytest.mark.asyncio
async def test_open_account_success(uow):
	"""Успешное открытие счета с генерацией номера и событиями."""
	user_id = uuid4()
	uow.accounts.count_open_by_type.return_value = 0
	uow.accounts.get_by_number.return_value = None  # Эмуляция уникальности номера
	uow.accounts.get_owner_contact.return_value = models.Contact(email="o@o.com")

	payload = schemas.OpenAccountRequest(type="checking", currency="RUB")
	acc = await open_account(uow, user_id, payload)

	assert acc.client_id == user_id
	assert acc.status == "open"
	assert acc.type == "checking"
	assert uow.committed is True

	# Проверка регистрации событий
	assert any(isinstance(e, NotificationEvent) and e.type == "account_opened" for e in uow.events)
	assert any(isinstance(e, LogEvent) and e.action == "open_account" for e in uow.events)

	uow.accounts.add.assert_called_once()
	uow.accounts.refresh.assert_awaited_once_with(acc)


# --- Тесты list_accounts / get_account (CQRS Layer) ---


@pytest.mark.asyncio
async def test_list_accounts(uow):
	"""Получение списка счетов через Query Layer."""
	user_id = uuid4()
	mock_data = (
		[
			schemas.AccountResponse(
				id=uuid4(),
				client_id=user_id,
				account_number="1",
				type="checking",
				currency="RUB",
				balance=Decimal("0.00"),
				status="open",
				opened_at=datetime.now(UTC),
			)
		],
		1,
	)
	uow.account_queries.list_by_user_with_total.return_value = mock_data

	accounts, total = await list_accounts(uow, user_id)
	assert total == 1
	assert len(accounts) == 1
	assert accounts[0].account_number == "1"


@pytest.mark.asyncio
async def test_get_account_success(uow):
	"""Получение деталей счета через Query Layer."""
	user_id = uuid4()
	acc_id = uuid4()
	mock_acc = schemas.AccountResponse(
		id=acc_id,
		client_id=user_id,
		account_number="123",
		type="savings",
		currency="USD",
		balance=Decimal("10.00"),
		status="frozen",
		opened_at=datetime.now(UTC),
	)
	uow.account_queries.get_by_id_raw.return_value = mock_acc

	res = await get_account(uow, user_id, acc_id)
	assert res.id == acc_id
	assert res.currency == "USD"


@pytest.mark.asyncio
async def test_get_account_not_found(uow):
	"""Ошибка, если Query Layer не нашел счет."""
	uow.account_queries.get_by_id_raw.return_value = None

	with pytest.raises(AccountNotFound):
		await get_account(uow, uuid4(), uuid4())
