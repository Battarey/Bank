import pytest
import uuid
from decimal import Decimal
from datetime import datetime, UTC
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock

from shared.models import BankAccount, User, Contact
from shared.utils.security import get_blind_index

async def create_test_user(db_session: AsyncSession, user_id: uuid.UUID, email: str = "test@example.com", phone: str = "+79001112233"):
	user = User(id=user_id, status="active", is_verified=True, created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
	contact = Contact(
		client_id=user_id, email=email, phone=phone,
		email_hash=get_blind_index(email), phone_hash=get_blind_index(phone)
	)
	db_session.add(user)
	await db_session.flush()
	db_session.add(contact)
	await db_session.commit()


@pytest.mark.asyncio
async def test_exchange_success(client: AsyncClient, db_session: AsyncSession, monkeypatch):
	"""Тест успешного обмена RUB -> USD."""
	user_id = uuid.uuid4()
	await create_test_user(db_session, user_id)
	
	# 1. Создаем счета
	acc_rub = BankAccount(
		id=uuid.uuid4(), client_id=user_id, account_number="RUB_ACC",
		type="current", currency="RUB", balance=Decimal("10000.00"),
		status="open", opened_at=datetime.now(UTC)
	)
	acc_usd = BankAccount(
		id=uuid.uuid4(), client_id=user_id, account_number="USD_ACC",
		type="current", currency="USD", balance=Decimal("0.00"),
		status="open", opened_at=datetime.now(UTC)
	)
	db_session.add_all([acc_rub, acc_usd])
	await db_session.commit()
	
	# 2. Мокаем курс RUB/USD = 0.01 (1 доллар = 100 рублей)
	from currency_service import exchange_client
	monkeypatch.setattr(exchange_client, "_fetch_rates", AsyncMock(return_value={
		"result": "success",
		"base_code": "RUB",
		"conversion_rates": {"USD": 0.01},
		"time_last_update_unix": int(datetime.now(UTC).timestamp())
	}))
	
	# 3. Обмениваем 5000 RUB
	payload = {
		"from_account_id": str(acc_rub.id),
		"to_account_id": str(acc_usd.id),
		"amount": "5000.00"
	}
	response = await client.post("/exchange", json=payload, headers={"X-User-Id": str(user_id)})
	assert response.status_code == 200
	data = response.json()
	
	assert data["from_amount"] == "5000.00"
	assert data["to_amount"] == "50.00" # 5000 * 0.01
	assert data["rate"] == "0.01"
	
	# 4. Проверяем остатки в БД
	await db_session.refresh(acc_rub)
	await db_session.refresh(acc_usd)
	assert acc_rub.balance == Decimal("5000.00")
	assert acc_usd.balance == Decimal("50.00")


@pytest.mark.asyncio
async def test_exchange_insufficient_funds(client: AsyncClient, db_session: AsyncSession):
	"""Тест обмена при нехватке средств."""
	user_id = uuid.uuid4()
	await create_test_user(db_session, user_id, email="low_funds@example.com", phone="+79001234567")
	
	acc1 = BankAccount(id=uuid.uuid4(), client_id=user_id, account_number="ACC1", type="current", currency="RUB", balance=Decimal("100.00"), status="open", opened_at=datetime.now(UTC))
	acc2 = BankAccount(id=uuid.uuid4(), client_id=user_id, account_number="ACC2", type="current", currency="USD", balance=Decimal("0.00"), status="open", opened_at=datetime.now(UTC))
	db_session.add_all([acc1, acc2])
	await db_session.commit()
	
	payload = {"from_account_id": str(acc1.id), "to_account_id": str(acc2.id), "amount": "500.00"}
	response = await client.post("/exchange", json=payload, headers={"X-User-Id": str(user_id)})
	assert response.status_code == 422
	assert "Недостаточно средств" in response.json()["detail"]


@pytest.mark.asyncio
async def test_exchange_same_currency(client: AsyncClient, db_session: AsyncSession):
	"""Тест обмена между счетами одной валюты."""
	user_id = uuid.uuid4()
	await create_test_user(db_session, user_id, email="same_curr@example.com", phone="+79007654321")
	
	acc1 = BankAccount(id=uuid.uuid4(), client_id=user_id, account_number="ACC_R1", type="current", currency="RUB", balance=Decimal("1000.00"), status="open", opened_at=datetime.now(UTC))
	acc2 = BankAccount(id=uuid.uuid4(), client_id=user_id, account_number="ACC_R2", type="current", currency="RUB", balance=Decimal("0.00"), status="open", opened_at=datetime.now(UTC))
	db_session.add_all([acc1, acc2])
	await db_session.commit()
	
	payload = {"from_account_id": str(acc1.id), "to_account_id": str(acc2.id), "amount": "100.00"}
	response = await client.post("/exchange", json=payload, headers={"X-User-Id": str(user_id)})
	assert response.status_code == 409
	assert "Валюты совпадают" in response.json()["detail"]


@pytest.mark.asyncio
async def test_exchange_unauthorized(client: AsyncClient):
	"""Попытка обмена без заголовка X-User-Id."""
	payload = {"from_account_id": str(uuid.uuid4()), "to_account_id": str(uuid.uuid4()), "amount": "100.00"}
	response = await client.post("/exchange", json=payload)
	assert response.status_code == 422 # FastAPI Header(...) required


@pytest.mark.asyncio
async def test_exchange_frozen_account(client: AsyncClient, db_session: AsyncSession, monkeypatch):
	"""Запрет обмена со счета в статусе frozen."""
	user_id = uuid.uuid4()
	await create_test_user(db_session, user_id, email="frozen_exc@example.com", phone="+79008889900")
	
	acc_frozen = BankAccount(
		id=uuid.uuid4(), client_id=user_id, account_number="FROZEN_EXC",
		type="current", currency="RUB", balance=Decimal("1000.00"),
		status="frozen", opened_at=datetime.now(UTC)
	)
	acc_usd = BankAccount(
		id=uuid.uuid4(), client_id=user_id, account_number="USD_EXC",
		type="current", currency="USD", balance=Decimal("0.00"),
		status="open", opened_at=datetime.now(UTC)
	)
	db_session.add_all([acc_frozen, acc_usd])
	await db_session.commit()
	
	payload = {"from_account_id": str(acc_frozen.id), "to_account_id": str(acc_usd.id), "amount": "100.00"}
	response = await client.post("/exchange", json=payload, headers={"X-User-Id": str(user_id)})
	assert response.status_code == 409
	assert "frozen" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_exchange_other_user_account(client: AsyncClient, db_session: AsyncSession):
	"""Запрет обмена средствами чужого счета."""
	attacker_id = uuid.uuid4()
	victim_id = uuid.uuid4()
	await create_test_user(db_session, attacker_id, email="attacker@example.com", phone="+79111111111")
	await create_test_user(db_session, victim_id, email="victim@example.com", phone="+79222222222")
	
	acc_victim = BankAccount(
		id=uuid.uuid4(), client_id=victim_id, account_number="VICTIM_ACC",
		type="current", currency="RUB", balance=Decimal("1000.00"),
		status="open", opened_at=datetime.now(UTC)
	)
	acc_attacker = BankAccount(
		id=uuid.uuid4(), client_id=attacker_id, account_number="ATTACKER_ACC",
		type="current", currency="USD", balance=Decimal("0.00"),
		status="open", opened_at=datetime.now(UTC)
	)
	db_session.add_all([acc_victim, acc_attacker])
	await db_session.commit()
	
	payload = {"from_account_id": str(acc_victim.id), "to_account_id": str(acc_attacker.id), "amount": "100.00"}
	response = await client.post("/exchange", json=payload, headers={"X-User-Id": str(attacker_id)})
	assert response.status_code == 404
	assert "не найден" in response.json()["detail"]


@pytest.mark.asyncio
async def test_exchange_closed_account(client: AsyncClient, db_session: AsyncSession):
	"""Запрет обмена для закрытого счета."""
	user_id = uuid.uuid4()
	await create_test_user(db_session, user_id, email="closed_exc@example.com", phone="+79333333333")
	
	acc_closed = BankAccount(
		id=uuid.uuid4(), client_id=user_id, account_number="CLOSED_EXC",
		type="current", currency="RUB", balance=Decimal("1000.00"),
		status="closed", opened_at=datetime.now(UTC)
	)
	acc_usd = BankAccount(
		id=uuid.uuid4(), client_id=user_id, account_number="USD_EXC_2",
		type="current", currency="USD", balance=Decimal("0.00"),
		status="open", opened_at=datetime.now(UTC)
	)
	db_session.add_all([acc_closed, acc_usd])
	await db_session.commit()
	
	payload = {"from_account_id": str(acc_closed.id), "to_account_id": str(acc_usd.id), "amount": "100.00"}
	response = await client.post("/exchange", json=payload, headers={"X-User-Id": str(user_id)})
	assert response.status_code == 409
	assert "closed" in response.json()["detail"].lower()
