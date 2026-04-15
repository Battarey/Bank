from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from auth_service.core.exceptions import (
	AuthAlreadyBlocked,
	AuthNotFound,
)
from auth_service.services.session import (
	logout,
	logout_all,
	self_block,
)
from shared import models

# --- Тесты logout / logout_all ---


@pytest.mark.asyncio
@patch("auth_service.services.session.session_tokens")
async def test_logout_success(mock_tokens):
	"""Успешное удаление токена сессии."""
	mock_tokens.delete_token = AsyncMock()
	token = "active_token_123"
	await logout(token)
	mock_tokens.delete_token.assert_awaited_once_with(token)


@pytest.mark.asyncio
@patch("auth_service.services.session.session_tokens")
async def test_logout_all_success(mock_tokens):
	"""Успешный отзыв всех сессий пользователя."""
	mock_tokens.revoke_all = AsyncMock()
	user_id = uuid4()
	await logout_all(user_id)
	mock_tokens.revoke_all.assert_awaited_once_with(user_id)


# --- Тесты self_block ---


@pytest.fixture
def user_contact_tuple():
	"""Фикстура для пользователя и его контактов."""
	user = models.User(id=uuid4(), status="active")
	contact = models.Contact(client_id=user.id, email="user@example.com")
	return user, contact


@pytest.mark.asyncio
async def test_self_block_user_not_found(uow):
	"""Ошибка самоблокировки, если пользователь не найден."""
	uow.users.get_user_with_contact.side_effect = AuthNotFound("User not found")

	with pytest.raises(AuthNotFound):
		await self_block(uow, uuid4())


@pytest.mark.asyncio
async def test_self_block_already_blocked(uow, user_contact_tuple):
	"""Ошибка самоблокировки, если аккаунт уже заблокирован."""
	user, contact = user_contact_tuple
	user.status = "blocked"
	uow.users.get_user_with_contact.return_value = (user, contact)

	with pytest.raises(AuthAlreadyBlocked):
		await self_block(uow, user.id)


@pytest.mark.asyncio
@patch("auth_service.services.session.session_tokens")
async def test_self_block_success(mock_tokens, uow, user_contact_tuple):
	"""Успешная самоблокировка с заморозкой счетов и событиями."""
	mock_tokens.revoke_all = AsyncMock()
	user, contact = user_contact_tuple
	uow.users.get_user_with_contact.return_value = (user, contact)

	# Имитация открытых счетов
	acc1 = models.BankAccount(id=uuid4(), status="open")
	acc2 = models.BankAccount(id=uuid4(), status="open")
	uow.users.get_open_accounts.return_value = [acc1, acc2]

	await self_block(uow, user.id)

	assert user.status == "blocked"
	assert acc1.status == "frozen"
	assert acc1.frozen_by == "system"
	assert acc2.status == "frozen"

	assert uow.committed is True
	# Проверка отзыва сессий ПОСЛЕ коммита
	mock_tokens.revoke_all.assert_awaited_once_with(user.id)

	# Проверка событий
	assert any(e.type == "account_self_blocked" for e in uow.events)
	assert any(getattr(e, "action", None) == "self_block" for e in uow.events)
