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
async def test_process_event_no_user_id(clickhouse_client):
	"""Тест события без user_id (должно пропустить History, но записать в ClickHouse)."""
	event_data = {
		"type": "system.maintenance",
		"payload": {
			"service": "ops",
			"details": "Maintenance started"
		}
	}
	
	msg = MockMessage(event_data)
	await _process_message(msg)
	
	# 1. Проверяем Postgres History (должно быть пусто)
	async with HistorySessionLocal() as session:
		result = await session.execute(select(UserAction))
		assert len(result.scalars().all()) == 0

	# 2. Проверяем ClickHouse (должно записаться с нулевым user_id)
	res = await clickhouse_client.query(
		"SELECT event_type, details FROM business_events WHERE service = 'ops'"
	)
	assert len(res.result_rows) == 1
	assert res.result_rows[0][0] == "system.maintenance"
