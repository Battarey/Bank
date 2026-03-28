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


@pytest.mark.asyncio
async def test_open_account_invalid_data(client: AsyncClient, test_user: User):
	"""Ошибки валидации при открытии счета."""
	
	# Невалидная валюта
	response = await client.post(
		"/accounts",
		json={"type": "checking", "currency": "XYZ"},
		headers={"X-User-ID": str(test_user.id)}
	)
	assert response.status_code == 422

	# Невалидный тип
	response = await client.post(
		"/accounts",
		json={"type": "investment", "currency": "RUB"},
		headers={"X-User-ID": str(test_user.id)}
	)
	assert response.status_code == 422


@pytest.mark.asyncio
async def test_access_control_violations(client: AsyncClient, db_session: AsyncSession, test_user: User):
	"""Проверка изоляции данных между пользователями."""
	
	# 1. Создаем счет для первого пользователя
	account_id = uuid.uuid4()
	acc = BankAccount(
		id=account_id, client_id=test_user.id, account_number="ACC1",
		type="checking", currency="RUB", balance=0, status="open", opened_at=datetime.now()
	)
	db_session.add(acc)
	await db_session.commit()

	# 2. Создаем второго пользователя
	other_user_id = uuid.uuid4()
	other_user = User(id=other_user_id, status="active", is_verified=True, created_at=datetime.now(), updated_at=datetime.now())
	db_session.add(other_user)
	await db_session.commit()

	# 3. Пытаемся получить чужой счет
	response = await client.get(f"/accounts/{account_id}", headers={"X-User-ID": str(other_user_id)})
	assert response.status_code == 404 # service.get_account должен кидать AccountNotFound если client_id не совпадает

	# 4. Пытаемся заморозить чужой счет
	response = await client.post(f"/accounts/{account_id}/freeze", headers={"X-User-ID": str(other_user_id)})
	assert response.status_code == 404


@pytest.mark.asyncio
async def test_account_freeze_unfreeze_lifecycle(client: AsyncClient, db_session: AsyncSession, test_user: User):
	"""Тестирование жизненного цикла заморозки/разморозки."""
	
	# Создаем счет
	account_id = uuid.uuid4()
	acc = BankAccount(
		id=account_id, client_id=test_user.id, account_number="FREEZE_ME",
		type="checking", currency="RUB", balance=10, status="open", opened_at=datetime.now()
	)
	db_session.add(acc)
	await db_session.commit()

	# 1. Замораживаем
	response = await client.post(f"/accounts/{account_id}/freeze", headers={"X-User-ID": str(test_user.id)})
	assert response.status_code == 200
	assert response.json()["account"]["status"] == "frozen"

	# 2. Повторная заморозка
	response = await client.post(f"/accounts/{account_id}/freeze", headers={"X-User-ID": str(test_user.id)})
	assert response.status_code == 409
	assert "уже заморожен" in response.json()["detail"].lower()

	# 3. Размораживаем
	response = await client.post(f"/accounts/{account_id}/unfreeze", headers={"X-User-ID": str(test_user.id)})
	assert response.status_code == 200
	assert response.json()["account"]["status"] == "open"

	# 4. Повторная разморозка
	response = await client.post(f"/accounts/{account_id}/unfreeze", headers={"X-User-ID": str(test_user.id)})
	assert response.status_code == 409


@pytest.mark.asyncio
async def test_close_account_scenarios(client: AsyncClient, db_session: AsyncSession, test_user: User):
	"""Тестирование закрытия счета."""

	# 1. Закрытие счета с балансом
	acc_with_money_id = uuid.uuid4()
	acc1 = BankAccount(
		id=acc_with_money_id, client_id=test_user.id, account_number="MONEY",
		type="checking", currency="RUB", balance=100.0, status="open", opened_at=datetime.now()
	)
	db_session.add(acc1)
	await db_session.commit()

	response = await client.post(f"/accounts/{acc_with_money_id}/close", headers={"X-User-ID": str(test_user.id)})
	assert response.status_code == 409
	assert "остаток" in response.json()["detail"].lower()

	# 2. Успешное закрытие пустого счета
	acc_empty_id = uuid.uuid4()
	acc2 = BankAccount(
		id=acc_empty_id, client_id=test_user.id, account_number="EMPTY",
		type="checking", currency="RUB", balance=0, status="open", opened_at=datetime.now()
	)
	db_session.add(acc2)
	await db_session.commit()

	response = await client.post(f"/accounts/{acc_empty_id}/close", headers={"X-User-ID": str(test_user.id)})
	assert response.status_code == 200
	assert response.json()["account"]["status"] == "closed"

	# 3. Повторное закрытие
	response = await client.post(f"/accounts/{acc_empty_id}/close", headers={"X-User-ID": str(test_user.id)})
	assert response.status_code == 409
	assert "статусом «closed»" in response.json()["detail"].lower()
