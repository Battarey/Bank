import asyncio
import os
import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from unittest.mock import AsyncMock

from notification_service.store import init_mongo, close_mongo
from notification_service import main as notification_main

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongodb_test:27017/test_notifications_db")

@pytest_asyncio.fixture(scope="session")
def event_loop():
	loop = asyncio.get_event_loop_policy().new_event_loop()
	yield loop
	loop.close()

@pytest_asyncio.fixture(autouse=True)
async def setup_mongo():
	"""Инициализация и очистка MongoDB перед тестами."""
	# Переопределяем URL для тестов
	import notification_service.store.client as mongo_client
	mongo_client.MONGO_URL = MONGO_URL
	
	await init_mongo()
	db = AsyncIOMotorClient(MONGO_URL).get_default_database()
	await db["email_log"].delete_many({})
	
	yield
	
	await close_mongo()

@pytest_asyncio.fixture
async def mock_smtp(monkeypatch):
	"""Мок для aiosmtplib.send."""
	mock = AsyncMock()
	monkeypatch.setattr("aiosmtplib.send", mock)
	return mock
