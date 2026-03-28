import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from shared.clickhouse_core import init_clickhouse, close_clickhouse
from shared.history_core import history_engine, HistoryBase
from log_service import main as log_main

@pytest_asyncio.fixture(scope="session")
def event_loop():
	"""Создает event loop для всей сессии тестов."""
	loop = asyncio.get_event_loop_policy().new_event_loop()
	yield loop
	loop.close()

@pytest_asyncio.fixture(autouse=True)
async def setup_databases():
	"""Инициализация таблиц перед тестами."""
	# 1. Postgres History
	async with history_engine.begin() as conn:
		await conn.run_sync(HistoryBase.metadata.drop_all)
		await conn.run_sync(HistoryBase.metadata.create_all)
	
	# 2. ClickHouse
	await init_clickhouse()
	from clickhouse_connect.driver.asyncclient import AsyncClient
	import shared.clickhouse_core.client as ch_client
	if ch_client._client:
		await ch_client._client.command("TRUNCATE TABLE IF EXISTS business_events")
	
	yield
	
	await close_clickhouse()
	await history_engine.dispose()

@pytest_asyncio.fixture
async def clickhouse_client():
	"""Фикстура для прямого доступа к ClickHouse в тестах."""
	import shared.clickhouse_core.client as ch_client
	return ch_client._client
