import json
import pytest
from unittest.mock import MagicMock, AsyncMock
from notification_service.main import _process_message
from notification_service.store import get_mongo

class MockMessage:
	"""Имитация сообщения aio_pika."""
	def __init__(self, body: dict):
		self.body = json.dumps(body).encode()
		self.process = MagicMock()
		self.process.return_value.__aenter__ = AsyncMock()
		self.process.return_value.__aexit__ = AsyncMock()

@pytest.mark.asyncio
async def test_process_verification_code_success(mock_smtp):
	"""Тест успешной отправки кода верификации."""
	email = "user@example.com"
	code = "123456"
	
	event_data = {
		"type": "verification_code",
		"payload": {
			"to": email,
			"variables": {
				"code": code
			}
		}
	}
	
	# 1. Запускаем обработку
	msg = MockMessage(event_data)
	await _process_message(msg)
	
	# 2. Проверяем мок SMTP
	assert mock_smtp.called
	args, kwargs = mock_smtp.call_args
	email_msg = args[0]
	assert email_msg["To"] == email
	assert code in email_msg.get_content()
	
	# 3. Проверяем MongoDB
	db = get_mongo()
	doc = await db["email_log"].find_one({"to": email})
	assert doc is not None
	assert doc["type"] == "verification_code"
	assert doc["status"] == "sent"
	assert doc["variables"]["code"] == code

@pytest.mark.asyncio
async def test_process_unknown_template_fail():
	"""Тест обработки неизвестного шаблона."""
	email = "fail@example.com"
	event_data = {
		"type": "non_existent_template",
		"payload": {
			"to": email,
			"variables": {}
		}
	}
	
	msg = MockMessage(event_data)
	await _process_message(msg)
	
	# Проверяем MongoDB: статус должен быть failed
	db = get_mongo()
	doc = await db["email_log"].find_one({"to": email})
	assert doc is not None
	assert doc["status"] == "failed"
	assert "не найден" in doc["error"]

@pytest.mark.asyncio
async def test_process_smtp_error(monkeypatch):
	"""Тест ошибки при отправке SMTP."""
	import aiosmtplib
	monkeypatch.setattr("aiosmtplib.send", AsyncMock(side_effect=RuntimeError("SMTP connection failed")))
	
	email = "smtp_error@example.com"
	event_data = {
		"type": "welcome",
		"payload": {
			"to": email,
			"variables": {"name": "Test User"}
		}
	}
	
	msg = MockMessage(event_data)
	await _process_message(msg)
	
	# Проверяем MongoDB: статус должен быть failed
	db = get_mongo()
	doc = await db["email_log"].find_one({"to": email})
	assert doc is not None
	assert doc["status"] == "failed"
	assert "SMTP connection failed" in doc["error"]
