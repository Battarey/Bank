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
@pytest.mark.asyncio
async def test_process_invalid_json_robustness(caplog):
	"""Тест обработки невалидного JSON (не должен ронять воркер)."""
	msg = MockMessage({})
	msg.body = b"invalid json data {{["
	
	await _process_message(msg)
	assert "Невалидный JSON" in caplog.text


@pytest.mark.asyncio
async def test_process_missing_to_field():
	"""Тест обработки сообщения без поля 'to' (KeyError)."""
	event_data = {
		"type": "welcome",
		"payload": {
			"variables": {"name": "No To User"}
		}
	}
	
	msg = MockMessage(event_data)
	await _process_message(msg)
	
	# Проверяем MongoDB: статус должен быть failed
	db = get_mongo()
	doc = await db["email_log"].find_one({"variables.name": "No To User"})
	assert doc is not None
	assert doc["status"] == "failed"
	assert "to" in doc["error"].lower()


@pytest.mark.asyncio
async def test_process_missing_variables_error():
	"""Тест рендеринга шаблона с неполным набором данных (KeyError)."""
	email = "missing_vars@example.com"
	event_data = {
		"type": "verification_code", # Ожидает переменную 'code'
		"payload": {
			"to": email,
			"variables": {} # Пустые переменные
		}
	}
	
	msg = MockMessage(event_data)
	await _process_message(msg)
	
	# Проверяем MongoDB: статус должен быть failed
	db = get_mongo()
	doc = await db["email_log"].find_one({"to": email})
	assert doc is not None
	assert doc["status"] == "failed"
	assert "code" in doc["error"].lower()


@pytest.mark.asyncio
async def test_process_mongodb_down_robustness(monkeypatch, mock_smtp):
	"""Тест: сбой MongoDB не должен мешать отправке SMTP (хотя ошибка залогируется)."""
	from notification_service import store
	monkeypatch.setattr(store, "save_notification", AsyncMock(side_effect=Exception("MongoDB connection lost")))
	
	email = "db_down@example.com"
	event_data = {
		"type": "welcome",
		"payload": {
			"to": email,
			"variables": {"name": "DB Down User"}
		}
	}
	
	msg = MockMessage(event_data)
	# Мы ожидаем, что send_email выполнится, а save_notification упадет, но не уронит весь процесс
	await _process_message(msg)
	
	# Проверяем SMTP - письмо должно быть отправлено до падения сохранения
	assert mock_smtp.called
	args, _ = mock_smtp.call_args
	assert args[0]["To"] == email


@pytest.mark.asyncio
async def test_process_large_vars_stress(mock_smtp):
	"""Тест обработки экстремально длинных строк в переменных шаблона."""
	email = "large@example.com"
	long_code = "X" * 10000 # 10KB код
	
	event_data = {
		"type": "verification_code",
		"payload": {
			"to": email,
			"variables": {"code": long_code}
		}
	}
	
	msg = MockMessage(event_data)
	await _process_message(msg)
	
	# Проверяем SMTP
	assert mock_smtp.called
	args, _ = mock_smtp.call_args
	assert long_code in args[0].get_content()
	
	# Проверяем MongoDB
	db = get_mongo()
	doc = await db["email_log"].find_one({"to": email})
	assert doc["variables"]["code"] == long_code
