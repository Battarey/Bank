import uuid
from decimal import Decimal
from datetime import datetime, UTC

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.models import User, BankAccount, Transaction, Contact
from shared.utils.security import get_blind_index

@pytest.fixture
def mock_user_id():
	return uuid.uuid4()

async def create_test_user(db_session: AsyncSession, user_id: uuid.UUID, email: str = "test@example.com", phone: str = "+79001234567"):
	"""Вспомогательная функция для создания пользователя с контактом."""
	user = User(
		id=user_id, 
		created_at=datetime.now(UTC), 
		updated_at=datetime.now(UTC),
		status="active",
		is_verified=True
	)
	contact = Contact(
		client_id=user_id,
		email=email,
		phone=phone,
		email_hash=get_blind_index(email),
		phone_hash=get_blind_index(phone)
	)
	db_session.add(user)
	await db_session.flush()
	
	db_session.add(contact)
	await db_session.flush()
	return user

@pytest.mark.asyncio
async def test_deposit_success(client: AsyncClient, db_session: AsyncSession, mock_user_id):
	"""Тест успешного пополнения счета."""
	# 1. Создаем пользователя и счет
	await create_test_user(db_session, mock_user_id)
	
	account = BankAccount(
		id=uuid.uuid4(),
		client_id=mock_user_id,
		account_number="DEP1234567890",
		type="current",
		currency="RUB",
		balance=Decimal("0.00"),
		status="open",
		opened_at=datetime.now(UTC)
	)
	db_session.add(account)
	await db_session.commit()
	
	# 2. Пополняем счет
	payload = {
		"amount": "1000.50",
		"description": "Test deposit"
	}
	response = await client.post(
		f"/accounts/{account.id}/deposit", 
		json=payload,
		headers={"X-User-Id": str(mock_user_id)}
	)
	assert response.status_code == 200
	data = response.json()
	assert data["transaction"]["amount"] == "1000.50"
	
	# 3. Проверяем баланс в БД
	await db_session.refresh(account)
	assert account.balance == Decimal("1000.50")
	
	# 4. Проверяем наличие транзакции
	stmt = select(Transaction).where(Transaction.account_id == account.id).where(Transaction.type == "deposit")
	result = await db_session.execute(stmt)
	tx = result.scalar()
	assert tx is not None
	assert tx.amount == Decimal("1000.50")

@pytest.mark.asyncio
async def test_transfer_between_own_accounts(client: AsyncClient, db_session: AsyncSession, mock_user_id):
	"""Тест перевода между своими счетами."""
	# 1. Создаем пользователя и два счета
	await create_test_user(db_session, mock_user_id)
	
	acc1 = BankAccount(
		id=uuid.uuid4(), client_id=mock_user_id, account_number="TRA1",
		type="current", currency="RUB", balance=Decimal("5000.00"),
		status="open", opened_at=datetime.now(UTC)
	)
	acc2 = BankAccount(
		id=uuid.uuid4(), client_id=mock_user_id, account_number="TRA2",
		type="current", currency="RUB", balance=Decimal("0.00"),
		status="open", opened_at=datetime.now(UTC)
	)
	db_session.add_all([acc1, acc2])
	await db_session.commit()
	
	# 2. Выполняем перевод
	payload = {
		"to_account_id": str(acc2.id),
		"amount": "2000.00",
		"description": "Internal transfer"
	}
	response = await client.post(
		f"/accounts/{acc1.id}/transfer", 
		json=payload, 
		headers={"X-User-Id": str(mock_user_id)}
	)
	assert response.status_code == 200
	
	# 3. Проверяем балансы
	await db_session.refresh(acc1)
	await db_session.refresh(acc2)
	assert acc1.balance == Decimal("3000.00")
	assert acc2.balance == Decimal("2000.00")

@pytest.mark.asyncio
async def test_transfer_security_block(client: AsyncClient, db_session: AsyncSession, mock_user_id, monkeypatch):
	"""Тест блокировки перевода системой безопасности."""
	# 1. Создаем пользователей и счета
	recipient_id = uuid.uuid4()
	await create_test_user(db_session, mock_user_id, email="sender@example.com", phone="+79001111111")
	await create_test_user(db_session, recipient_id, email="recipient@example.com", phone="+79002222222")
	
	acc1 = BankAccount(
		id=uuid.uuid4(), client_id=mock_user_id, account_number="SEC1",
		type="current", currency="RUB", balance=Decimal("1000000.00"),
		status="open", opened_at=datetime.now(UTC)
	)
	acc2 = BankAccount(
		id=uuid.uuid4(), client_id=recipient_id, account_number="SEC2",
		type="current", currency="RUB", balance=Decimal("0.00"),
		status="open", opened_at=datetime.now(UTC)
	)
	db_session.add_all([acc1, acc2])
	await db_session.commit()
	
	# 2. Мокаем Security Service на блокировку
	from transaction_service import security_client
	from unittest.mock import AsyncMock
	monkeypatch.setattr(security_client, "check_transaction", AsyncMock(return_value=(False, [{"rule": "test_violation"}])))
	
	# 3. Пробуем перевести
	payload = {
		"to_account_id": str(acc2.id),
		"amount": "800000.00",
		"description": "Suspicious transfer"
	}
	response = await client.post(
		f"/accounts/{acc1.id}/transfer", 
		json=payload, 
		headers={"X-User-Id": str(mock_user_id)}
	)
	
	assert response.status_code == 403 # SecurityViolation -> 403
	assert "системой безопасности" in response.json()["detail"]
	
	# 4. Проверяем, что счет отправителя заморожен
	await db_session.refresh(acc1)
	assert acc1.status == "frozen"
	assert acc1.freeze_reason == "test_violation"

@pytest.mark.asyncio
async def test_get_history(client: AsyncClient, db_session: AsyncSession, mock_user_id):
	"""Тест получения истории транзакций."""
	# 1. Создаем данные
	await create_test_user(db_session, mock_user_id)
	
	account = BankAccount(
		id=uuid.uuid4(), client_id=mock_user_id, account_number="HIST1",
		type="current", currency="RUB", balance=Decimal("1000.00"),
		status="open", opened_at=datetime.now(UTC)
	)
	db_session.add(account)
	await db_session.flush()
	
	tx = Transaction(
		id=uuid.uuid4(), 
		account_id=account.id, 
		type="deposit", 
		amount=Decimal("1000.00"),
		direction="incoming", 
		balance_before=Decimal("0.00"), 
		balance_after=Decimal("1000.00"),
		status="posted", 
		created_at=datetime.now(UTC)
	)
	db_session.add(tx)
	await db_session.commit()
	
	# 2. Получаем историю
	response = await client.get(
		f"/accounts/{account.id}/transactions", 
		headers={"X-User-Id": str(mock_user_id)}
	)
	assert response.status_code == 200
	data = response.json()
	assert len(data["transactions"]) >= 1
	# Ищем нашу транзакцию
	found = any(item["amount"] == "1000.00" for item in data["transactions"])
	assert found

@pytest.mark.asyncio
async def test_withdraw_success(client: AsyncClient, db_session: AsyncSession, mock_user_id):
	"""Тест успешного снятия средств."""
	# 1. Создаем пользователя и счет с балансом
	await create_test_user(db_session, mock_user_id)
	
	account = BankAccount(
		id=uuid.uuid4(), client_id=mock_user_id, account_number="WTH1",
		type="current", currency="RUB", balance=Decimal("1000.00"),
		status="open", opened_at=datetime.now(UTC)
	)
	db_session.add(account)
	await db_session.commit()
	
	# 2. Снимаем средства
	payload = {
		"amount": "400.00",
		"description": "Test withdrawal"
	}
	response = await client.post(
		f"/accounts/{account.id}/withdraw", 
		json=payload, 
		headers={"X-User-Id": str(mock_user_id)}
	)
	assert response.status_code == 200
	
	# 3. Проверяем баланс
	await db_session.refresh(account)
	assert account.balance == Decimal("600.00")

@pytest.mark.asyncio
async def test_withdraw_insufficient_funds(client: AsyncClient, db_session: AsyncSession, mock_user_id):
	"""Тест снятия средств при недостаточном балансе."""
	# 1. Создаем пользователя и счет с низким балансом
	await create_test_user(db_session, mock_user_id)
	
	account = BankAccount(
		id=uuid.uuid4(), client_id=mock_user_id, account_number="WTH_FAIL",
		type="current", currency="RUB", balance=Decimal("100.00"),
		status="open", opened_at=datetime.now(UTC)
	)
	db_session.add(account)
	await db_session.commit()
	
	# 2. Пробуем снять больше, чем есть
	payload = {
		"amount": "500.00",
		"description": "Overdraft attempt"
	}
	response = await client.post(
		f"/accounts/{account.id}/withdraw", 
		json=payload, 
		headers={"X-User-Id": str(mock_user_id)}
	)
	
	assert response.status_code == 422 # InsufficientFunds -> 422
	assert "Недостаточно средств" in response.json()["detail"]
