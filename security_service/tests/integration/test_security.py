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
		direction="out",
		status="completed",
		balance_before=Decimal("100000.00"),
		balance_after=Decimal("100000.00") - previous_amount,
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


@pytest.mark.asyncio
async def test_check_daily_count_limit(client: AsyncClient, db_session: AsyncSession, setup_account):
	"""Проверка срабатывания правила daily_count_limit."""
	account_id = setup_account
	from security_service.rules import DAILY_TX_COUNT
	
	# Добавляем 20 транзакций (лимит)
	for i in range(DAILY_TX_COUNT):
		tx = Transaction(
			id=uuid.uuid4(), account_id=account_id, type="transfer",
			amount=Decimal("100"), direction="out", status="completed",
			balance_before=Decimal("1000"), balance_after=Decimal("900"),
			created_at=datetime.now(UTC)
		)
		db_session.add(tx)
	await db_session.commit()
	
	# 21-я транзакция должна нарушить лимит
	payload = {"account_id": str(account_id), "tx_type": "transfer", "amount": "100.00", "currency": "RUB"}
	response = await client.post("/check", json=payload)
	data = response.json()
	assert data["allowed"] is False
	assert any(v["rule"] == "daily_count_limit" for v in data["violations"])


@pytest.mark.asyncio
async def test_check_rapid_fire(client: AsyncClient, db_session: AsyncSession, setup_account):
	"""Проверка срабатывания правила rapid_fire."""
	account_id = setup_account
	from security_service.rules import RAPID_FIRE_COUNT
	
	# Создаем серию быстрых транзакций
	for _ in range(RAPID_FIRE_COUNT):
		tx = Transaction(
			id=uuid.uuid4(), account_id=account_id, type="transfer",
			amount=Decimal("10"), direction="out", status="completed",
			balance_before=Decimal("1000"), balance_after=Decimal("990"),
			created_at=datetime.now(UTC)
		)
		db_session.add(tx)
	await db_session.commit()
	
	payload = {"account_id": str(account_id), "tx_type": "transfer", "amount": "10.00", "currency": "RUB"}
	response = await client.post("/check", json=payload)
	data = response.json()
	assert data["allowed"] is False
	assert any(v["rule"] == "rapid_fire" for v in data["violations"])


@pytest.mark.asyncio
async def test_check_structuring(client: AsyncClient, db_session: AsyncSession, setup_account):
	"""Проверка срабатывания правила structuring (дробление)."""
	account_id = setup_account
	from security_service.rules import LARGE_TX_THRESHOLD, STRUCTURING_RATIO, STRUCTURING_MIN_HITS
	
	# Сумма чуть ниже порога
	struct_amount = LARGE_TX_THRESHOLD * STRUCTURING_RATIO + Decimal("1000")
	
	# Добавляем несколько таких транзакций
	for _ in range(STRUCTURING_MIN_HITS - 1):
		tx = Transaction(
			id=uuid.uuid4(), account_id=account_id, type="transfer",
			amount=struct_amount, direction="out", status="completed",
			balance_before=Decimal("1000000"), balance_after=Decimal("1000000") - struct_amount,
			created_at=datetime.now(UTC)
		)
		db_session.add(tx)
	await db_session.commit()
	
	payload = {"account_id": str(account_id), "tx_type": "transfer", "amount": str(struct_amount), "currency": "RUB"}
	response = await client.post("/check", json=payload)
	data = response.json()
	assert data["allowed"] is False
	assert any(v["rule"] == "structuring" for v in data["violations"])


@pytest.mark.asyncio
async def test_check_round_amount_pattern(client: AsyncClient, db_session: AsyncSession, setup_account):
	"""Проверка срабатывания правила round_amount_pattern."""
	account_id = setup_account
	from security_service.rules import ROUND_AMOUNT_FLOOR, ROUND_AMOUNT_MIN_HITS
	
	round_amount = ROUND_AMOUNT_FLOOR + Decimal("10000")
	
	for _ in range(ROUND_AMOUNT_MIN_HITS - 1):
		tx = Transaction(
			id=uuid.uuid4(), account_id=account_id, type="transfer",
			amount=round_amount, direction="out", status="completed",
			balance_before=Decimal("1000000"), balance_after=Decimal("1000000") - round_amount,
			created_at=datetime.now(UTC)
		)
		db_session.add(tx)
	await db_session.commit()
	
	payload = {"account_id": str(account_id), "tx_type": "transfer", "amount": str(round_amount), "currency": "RUB"}
	response = await client.post("/check", json=payload)
	data = response.json()
	assert data["allowed"] is False
	assert any(v["rule"] == "round_amount_pattern" for v in data["violations"])


@pytest.mark.asyncio
async def test_check_multiple_violations(client: AsyncClient, db_session: AsyncSession, setup_account):
	"""Проверка множественных нарушений одной транзакцией."""
	account_id = setup_account
	from security_service.rules import LARGE_TX_THRESHOLD, DAILY_AMOUNT_LIMIT
	
	# Транзакция, нарушающая и large_single_tx, и daily_amount_limit
	huge_amount = max(LARGE_TX_THRESHOLD, DAILY_AMOUNT_LIMIT) + Decimal("1000")
	
	payload = {"account_id": str(account_id), "tx_type": "transfer", "amount": str(huge_amount), "currency": "RUB"}
	response = await client.post("/check", json=payload)
	data = response.json()
	
	assert data["allowed"] is False
	rules = [v["rule"] for v in data["violations"]]
	assert "large_single_tx" in rules
	assert "daily_amount_limit" in rules


@pytest.mark.asyncio
async def test_check_api_negative_scenarios(client: AsyncClient):
	"""Негативные сценарии API."""
	
	# 1. Несуществующий счет
	payload = {"account_id": str(uuid.uuid4()), "tx_type": "transfer", "amount": "100.00", "currency": "RUB"}
	response = await client.post("/check", json=payload)
	assert response.status_code == 404

	# 2. Невалидный формат суммы
	payload = {"account_id": str(uuid.uuid4()), "tx_type": "transfer", "amount": "invalid", "currency": "RUB"}
	response = await client.post("/check", json=payload)
	assert response.status_code == 422
