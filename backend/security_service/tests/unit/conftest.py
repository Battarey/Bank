import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Устанавливаем переменные окружения
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("INTERNAL_API_KEY", "test-key")

# Вызываем bootstrap ПЕРЕД импортом UoW, так как там идет обращение к контейнеру на уровне модуля
from security_service.config import SecuritySettings
from shared.bootstrap import bootstrap

bootstrap(SecuritySettings)


@pytest.fixture(autouse=True)
def mock_bootstrap():
	"""Мокирует get_container для возврата настроек и сессии в тестах."""
	mock_settings = MagicMock()
	mock_settings.INTERNAL_API_KEY = "test-key"
	mock_settings.MONGO_URL = "mongodb://test"

	mock_container = MagicMock()
	mock_container.settings = mock_settings
	mock_container.session_factory = MagicMock()  # SQLAlchemy session factory

	with patch("security_service.uow.get_container", return_value=mock_container):
		yield mock_container


@pytest.fixture
def mock_session():
	"""Фикстура для имитации асинхронной сессии SQLAlchemy."""
	session = AsyncMock()
	return session


@pytest.fixture
def mock_aio_pika():
	"""Сложный мок для aio_pika."""
	mock_connection = AsyncMock()
	mock_channel = AsyncMock()
	mock_queue = AsyncMock()

	mock_connection.channel.return_value = mock_channel
	mock_channel.declare_queue.return_value = mock_queue

	# Поддержка async with connection
	mock_connection.__aenter__.return_value = mock_connection
	mock_connection.__aexit__.return_value = None

	return {
		"connection": mock_connection,
		"channel": mock_channel,
		"queue": mock_queue,
	}


@pytest.fixture
def mock_mongo_repo():
	"""Фикстура для мока SecurityEventRepository."""
	repo = AsyncMock()
	repo.save_event = AsyncMock()
	return repo


@pytest.fixture
def mock_uow():
	"""Фикстура-заглушка Unit of Work."""
	uow = MagicMock()
	uow.accounts = AsyncMock()
	uow.session = AsyncMock()

	# Мок контекстного менеджера
	uow.__aenter__ = AsyncMock(return_value=uow)
	uow.__aexit__ = AsyncMock(return_value=None)
	uow.commit = AsyncMock()
	uow.rollback = AsyncMock()
	uow.add_event = MagicMock()

	return uow
