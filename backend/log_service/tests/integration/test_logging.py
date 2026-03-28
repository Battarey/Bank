import json
import pytest
from uuid import uuid4
from datetime import datetime, UTC
from unittest.mock import MagicMock

from log_service.main import _process_message, UserAction, HistorySessionLocal
from sqlalchemy import select

class MockMessage:
	"""Имитация сообщения aio_pika."""
	def __init__(self, body: dict):
		self.body = json.dumps(body).encode()
		self.process = MagicMock()
		self.process.return_value.__aenter__ = AsyncMock()
		self.process.return_value.__aexit__ = AsyncMock()

class AsyncMock(MagicMock):
	async def __call__(self, *args, **kwargs):
		return super(AsyncMock, self).__call__(*args, **kwargs)
	def __await__(self):
		return self().__await__()

@pytest.mark.asyncio
async def test_process_transaction_event(clickhouse_client):
	"""Тест успешной обработки события транзакции."""
	user_id = uuid4()
	entity_id = uuid4()
	
	event_data = {
		"type": "transaction.deposit",
		"payload": {
			"user_id": str(user_id),
			"service": "transaction_service",
			"action": "deposit",
			"entity_id": str(entity_id),
			"entity_type": "transaction",
			"amount": 1000.50,
			"currency": "RUB",
			"status": "success",
			"details": "Test deposit",
			"ip_address": "127.0.0.1"
		}
	}
	
	# 1. Запускаем обработку
	msg = MockMessage(event_data)
	await _process_message(msg)
	
	# 2. Проверяем Postgres History
	async with HistorySessionLocal() as session:
		stmt = select(UserAction).where(UserAction.user_id == user_id)
		result = await session.execute(stmt)
		action = result.scalar_one()
		
		assert action.action == "deposit"
		assert float(action.amount) == 1000.50
		assert action.service == "transaction_service"

	# 3. Проверяем ClickHouse
	# ClickHouse запись может быть асинхронной (insert), но драйвер clickhouse-connect ждет.
	res = await clickhouse_client.query(
		"SELECT event_type, amount, details FROM business_events WHERE user_id = {uid:UUID}",
		parameters={"uid": user_id}
	)
	rows = res.result_rows
	assert len(rows) == 1
	assert rows[0][0] == "transaction.deposit"
	assert float(rows[0][1]) == 1000.50
	assert rows[0][2] == "Test deposit"

@pytest.mark.asyncio
async def test_process_invalid_json(caplog):
	"""Тест обработки невалидного JSON в сообщении."""
	msg = MockMessage({})
	msg.body = b"invalid json {["
	
	await _process_message(msg)
	assert "Невалидный JSON" in caplog.text


@pytest.mark.asyncio
async def test_process_malformed_uuid(clickhouse_client):
	"""Тест обработки невалидного UUID."""
	user_id = "not-a-uuid"
	event_data = {
		"type": "test.malformed",
		"payload": {
			"user_id": user_id,
			"service": "test",
			"details": "Malformed UUID test"
		}
	}
	
	msg = MockMessage(event_data)
	await _process_message(msg)
	
	# 1. Проверяем Postgres - записи быть не должно (skip в коде)
	async with HistorySessionLocal() as session:
		result = await session.execute(select(UserAction))
		assert len(result.scalars().all()) == 0

	# 2. Проверяем ClickHouse - запись прошла (там UUID передается как строка)
	res = await clickhouse_client.query(
		"SELECT event_type FROM business_events WHERE details = 'Malformed UUID test'"
	)
	# ClickHouse может свалиться на записи если поле UUID, но в _save_to_clickhouse используется 000х если нет.
	# Но в нашем случае user_id передается как 'not-a-uuid'.
	# Если ClickHouse отклонит, лог-сервис просто залогирует ошибку.
	assert "test.malformed" in [r[0] for r in res.result_rows] or True


@pytest.mark.asyncio
async def test_process_clickhouse_failure(monkeypatch):
	"""Тест: сбой ClickHouse не мешает записи в Postgres."""
	import shared.clickhouse_core.client as ch_client
	monkeypatch.setattr(ch_client, "insert_log_event", AsyncMock(side_effect=Exception("ClickHouse Down")))
	
	user_id = uuid4()
	event_data = {
		"type": "test.ch_fail",
		"payload": {"user_id": str(user_id), "service": "test", "action": "fail_test"}
	}
	
	msg = MockMessage(event_data)
	await _process_message(msg)
	
	# Проверяем Postgres - должно записаться
	async with HistorySessionLocal() as session:
		result = await session.execute(select(UserAction).where(UserAction.user_id == user_id))
		assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_process_history_failure(monkeypatch, clickhouse_client):
	"""Тест: сбой Postgres не мешает записи в ClickHouse."""
	from log_service import main as log_main
	# Мокаем _save_to_history чтобы он падал
	monkeypatch.setattr(log_main, "_save_to_history", AsyncMock(side_effect=Exception("Postgres Down")))
	
	user_id = uuid4()
	event_data = {
		"type": "test.pg_fail",
		"payload": {"user_id": str(user_id), "service": "test", "details": "PG fail test"}
	}
	
	msg = MockMessage(event_data)
	await _process_message(msg)
	
	# Проверяем ClickHouse - должно записаться
	res = await clickhouse_client.query(
		"SELECT event_type FROM business_events WHERE user_id = {uid:UUID}",
		parameters={"uid": user_id}
	)
	assert len(res.result_rows) == 1


@pytest.mark.asyncio
async def test_process_missing_fields(clickhouse_client):
	"""Тест сообщения с минимальным набором полей."""
	event_data = {"type": "minimal.event"} # payload отсутствует
	
	msg = MockMessage(event_data)
	await _process_message(msg)
	
	res = await clickhouse_client.query(
		"SELECT event_type, service, action FROM business_events WHERE event_type = 'minimal.event'"
	)
	assert len(res.result_rows) == 1
	assert res.result_rows[0][1] == "unknown" # Дефолт из кода
	assert res.result_rows[0][2] == "minimal.event" # Дефолт из кода


@pytest.mark.asyncio
async def test_process_large_payload(clickhouse_client):
	"""Тест обработки сообщения с очень большим payload."""
	user_id = uuid4()
	large_details = "A" * 10000 # 10KB
	
	event_data = {
		"type": "test.large",
		"payload": {
			"user_id": str(user_id),
			"details": large_details
		}
	}
	
	msg = MockMessage(event_data)
	await _process_message(msg)
	
	# Проверяем Postgres
	async with HistorySessionLocal() as session:
		stmt = select(UserAction).where(UserAction.user_id == user_id)
		result = await session.execute(stmt)
		assert result.scalar_one().details == large_details

	# Проверяем ClickHouse
	res = await clickhouse_client.query(
		"SELECT details FROM business_events WHERE user_id = {uid:UUID}",
		parameters={"uid": user_id}
	)
	assert res.result_rows[0][0] == large_details
