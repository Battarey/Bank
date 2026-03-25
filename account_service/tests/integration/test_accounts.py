import uuid
from datetime import datetime
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from shared.models import BankAccount, User

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
	"""Создает тестового пользователя для привязки счетов."""
	user_id = uuid.uuid4()
	user = User(
		id=user_id,
		created_at=datetime.now(),
		updated_at=datetime.now(),
		status="active",
		is_verified=True
	)
	db_session.add(user)
	await db_session.commit()
	return user

@pytest.mark.asyncio
async def test_open_account(client: AsyncClient, db_session: AsyncSession, test_user: User):
	"""Интеграционный тест для открытия счета."""
	payload = {
		"type": "checking",
		"currency": "RUB"
	}
	
	response = await client.post(
		"/accounts",
		json=payload,
		headers={"X-User-ID": str(test_user.id)}
	)
	
	assert response.status_code == 201
	data = response.json()
	assert data["message"] == "Счёт успешно открыт."
	assert data["account"]["client_id"] == str(test_user.id)
	assert data["account"]["currency"] == "RUB"
	assert data["account"]["type"] == "checking"
	assert data["account"]["balance"] == "0.00"

@pytest.mark.asyncio
async def test_list_accounts(client: AsyncClient, db_session: AsyncSession, test_user: User):
	"""Интеграционный тест для получения списка счетов."""
	# Предварительно создаем счет напрямую в БД
	account = BankAccount(
		id=uuid.uuid4(),
		client_id=test_user.id,
		account_number="1234567890",
		type="savings",
		currency="USD",
		balance=100.0,
		status="open",
		opened_at=datetime.now()
	)
	db_session.add(account)
	await db_session.commit()
	
	response = await client.get(
		"/accounts",
		headers={"X-User-ID": str(test_user.id)}
	)
	
	assert response.status_code == 200
	data = response.json()
	assert data["total"] == 1
	assert data["accounts"][0]["account_number"] == "1234567890"
	assert data["accounts"][0]["currency"] == "USD"

@pytest.mark.asyncio
async def test_get_account_details(client: AsyncClient, db_session: AsyncSession, test_user: User):
	"""Интеграционный тест для получения деталей конкретного счета."""
	account_id = uuid.uuid4()
	
	# Создаем счет
	account = BankAccount(
		id=account_id,
		client_id=test_user.id,
		account_number="0987654321",
		type="checking",
		currency="EUR",
		balance=50.0,
		status="open",
		opened_at=datetime.now()
	)
	db_session.add(account)
	await db_session.commit()
	
	response = await client.get(
		f"/accounts/{account_id}",
		headers={"X-User-ID": str(test_user.id)}
	)
	
	assert response.status_code == 200
	data = response.json()
	assert data["id"] == str(account_id)
	assert data["account_number"] == "0987654321"
	assert data["balance"] == "50.0"

@pytest.mark.asyncio
async def test_get_account_not_found(client: AsyncClient, test_user: User):
	"""Тест на получение несуществующего счета."""
	random_id = uuid.uuid4()
	
	response = await client.get(
		f"/accounts/{random_id}",
		headers={"X-User-ID": str(test_user.id)}
	)
	
	assert response.status_code == 404
	assert "не найден" in response.json()["detail"].lower()
