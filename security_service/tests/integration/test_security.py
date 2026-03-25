import uuid
from decimal import Decimal
from datetime import datetime, UTC

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User, BankAccount, Transaction
from security_service.rules import LARGE_TX_THRESHOLD, DAILY_AMOUNT_LIMIT, DAILY_TX_COUNT
from security_service.store.client import _get_db, COLLECTION_NAME

@pytest.fixture
def mock_account():
	"""Фикстура для создания счета в БД."""
	user_id = uuid.uuid4()
	account_id = uuid.uuid4()
	return account_id, user_id

@pytest_asyncio.fixture(scope="function")
async def setup_account(db_session: AsyncSession, mock_account):
	account_id, user_id = mock_account
	user = User(
		id=user_id,
		created_at=datetime.now(UTC),
		updated_at=datetime.now(UTC)
	)
	db_session.add(user)
	await db_session.flush()
	
	account = BankAccount(
		id=account_id,
		client_id=user_id,
		account_number="SECTEST" + str(account_id)[:13],
		status="open",
		balance=Decimal("10000000.00"),
		currency="RUB",
		type="current",
		opened_at=datetime.now(UTC)
	)
	db_session.add(account)
	await db_session.commit()
	
	return account_id


@pytest.mark.asyncio
async def test_check_transaction_allowed(client: AsyncClient, setup_account):
	"""Проверка, что разрешенная транзакция (небольшая сумма) проходит."""
	account_id = setup_account
	
	payload = {
		"account_id": str(account_id),
		"tx_type": "transfer",
		"amount": "1000.00",
		"currency": "RUB"
	}
	
	response = await client.post("/check", json=payload)
	assert response.status_code == 200, response.json()
	data = response.json()
	
	assert data["allowed"] is True
	assert len(data["violations"]) == 0


@pytest.mark.asyncio
async def test_check_large_single_tx(client: AsyncClient, setup_account):
	"""Проверка срабатывания правила large_single_tx."""
	account_id = setup_account
	
	# Сумма больше порога (по умолчанию 600000)
	payload = {
		"account_id": str(account_id),
		"tx_type": "transfer",
		"amount": str(LARGE_TX_THRESHOLD + Decimal("1000")),
		"currency": "RUB"
	}
	
	response = await client.post("/check", json=payload)
	assert response.status_code == 200
	data = response.json()
	
	assert data["allowed"] is False
	assert len(data["violations"]) == 1
	
	violation = data["violations"][0]
	assert violation["rule"] == "large_single_tx"
	
	# Проверяем, что событие сохранилось в MongoDB
	db = _get_db()
	events = await db[COLLECTION_NAME].find({"account_id": str(account_id)}).to_list(length=10)
	assert len(events) == 1
	assert events[0]["rule"] == "large_single_tx"


@pytest.mark.asyncio
async def test_check_daily_amount_limit(client: AsyncClient, db_session: AsyncSession, setup_account):
	"""Проверка срабатывания правила daily_amount_limit (сумма за день)."""
	account_id = setup_account
	
	# Создаем транзакцию в БД, которая близка к дневному лимиту (лимит = 1 000 000)
	previous_amount = DAILY_AMOUNT_LIMIT - Decimal("1000")
	tx = Transaction(
		id=uuid.uuid4(),
		account_id=account_id,
		type="transfer",
		amount=previous_amount,
		currency="RUB",
		status="completed",
		created_at=datetime.now(UTC)
	)
	db_session.add(tx)
	await db_session.commit()
	
	# Новая транзакция на 2000 превысит дневной лимит
	payload = {
		"account_id": str(account_id),
		"tx_type": "transfer",
		"amount": "2000.00",
		"currency": "RUB"
	}
	
	response = await client.post("/check", json=payload)
	assert response.status_code == 200
	data = response.json()
	
	assert data["allowed"] is False
	
	violation = next((v for v in data["violations"] if v["rule"] == "daily_amount_limit"), None)
	assert violation is not None
