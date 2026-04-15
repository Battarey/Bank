from uuid import uuid4

import pytest

from account_service.core.exceptions import (
	AccountAlreadyFrozen,
	AccountNotFrozen,
	UnfreezeNotAllowed,
)
from account_service.services.account import (
	cascade_freeze,
	cascade_unfreeze,
	freeze_account,
	unfreeze_account,
)
from shared import models
from shared.events.base import LogEvent, NotificationEvent

# --- Тесты freeze_account ---


@pytest.mark.asyncio
async def test_freeze_account_already_frozen(uow):
	user_id = uuid4()
	acc = models.BankAccount(client_id=user_id, status="frozen", account_number="123")
	uow.accounts.get_by_user.return_value = acc

	with pytest.raises(AccountAlreadyFrozen):
		await freeze_account(uow, user_id, uuid4())


@pytest.mark.asyncio
async def test_freeze_account_success(uow):
	"""Успешная заморозка счета пользователем."""
	user_id = uuid4()
	acc = models.BankAccount(id=uuid4(), client_id=user_id, status="open", account_number="123")
	uow.accounts.get_by_user.return_value = acc
	uow.accounts.get_owner_contact.return_value = models.Contact(email="f@f.com")

	res = await freeze_account(uow, user_id, acc.id, reason="Security check")

	assert res.status == "frozen"
	assert res.frozen_by == "user"
	assert res.freeze_reason == "Security check"
	assert uow.committed is True

	# Проверка регистрации событий
	assert any(isinstance(e, NotificationEvent) and e.type == "account_frozen" for e in uow.events)
	assert any(isinstance(e, LogEvent) and e.action == "freeze_account" for e in uow.events)

	uow.accounts.refresh.assert_awaited_once_with(acc)


# --- Тесты unfreeze_account ---


@pytest.mark.asyncio
async def test_unfreeze_account_not_frozen(uow):
	user_id = uuid4()
	acc = models.BankAccount(client_id=user_id, status="open", account_number="123")
	uow.accounts.get_by_user.return_value = acc

	with pytest.raises(AccountNotFrozen):
		await unfreeze_account(uow, user_id, uuid4())


@pytest.mark.asyncio
async def test_unfreeze_account_system_locked(uow):
	"""Проверка запрета на самостоятельную разморозку, если счет заморожен системой."""
	user_id = uuid4()
	acc = models.BankAccount(client_id=user_id, status="frozen", frozen_by="system")
	uow.accounts.get_by_user.return_value = acc

	with pytest.raises(UnfreezeNotAllowed):
		await unfreeze_account(uow, user_id, uuid4())


@pytest.mark.asyncio
async def test_unfreeze_account_success(uow):
	"""Успешная разморозка счета пользователем."""
	user_id = uuid4()
	acc = models.BankAccount(id=uuid4(), client_id=user_id, status="frozen", frozen_by="user", account_number="123")
	uow.accounts.get_by_user.return_value = acc
	uow.accounts.get_owner_contact.return_value = models.Contact(email="f@f.com")

	res = await unfreeze_account(uow, user_id, acc.id)

	assert res.status == "open"
	assert res.frozen_by is None
	assert uow.committed is True
	assert any(isinstance(e, NotificationEvent) and e.type == "account_unfrozen" for e in uow.events)


# --- Тесты каскадных операций ---


@pytest.mark.asyncio
async def test_cascade_freeze_success(uow):
	"""Массовая заморозка всех открытых счетов пользователя."""
	user_id = uuid4()
	accs = [
		models.BankAccount(status="open", account_number="A1"),
		models.BankAccount(status="open", account_number="A2"),
	]
	uow.accounts.get_open_accounts.return_value = accs

	count = await cascade_freeze(uow, user_id, reason="Global lock")

	assert count == 2
	assert all(a.status == "frozen" for a in accs)
	assert all(a.frozen_by == "system" for a in accs)
	assert uow.committed is True
	assert len([e for e in uow.events if isinstance(e, LogEvent)]) == 2


@pytest.mark.asyncio
async def test_cascade_unfreeze_success(uow):
	"""Массовая разморозка счетов, которые были заморожены системой."""
	user_id = uuid4()
	accs = [models.BankAccount(status="frozen", frozen_by="system", account_number="A1")]
	uow.accounts.get_system_frozen_accounts.return_value = accs

	count = await cascade_unfreeze(uow, user_id)

	assert count == 1
	assert accs[0].status == "open"
	assert accs[0].frozen_by is None
	assert uow.committed is True
