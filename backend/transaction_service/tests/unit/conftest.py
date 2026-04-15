import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Устанавливаем переменные окружения
os.environ.setdefault("CURRENCY_SERVICE_URL", "http://currency:8001")
os.environ.setdefault("SECURITY_SERVICE_URL", "http://security:8002")
os.environ.setdefault("INTERNAL_API_KEY", "test-key")

# Вызываем bootstrap ПЕРЕД импортом UoW
from shared.bootstrap import bootstrap
from transaction_service.core.config import TransactionSettings

bootstrap(TransactionSettings)


@pytest.fixture(autouse=True)
def mock_bootstrap():
	"""Мокирует get_container для возврата настроек в тестах."""
	mock_settings = MagicMock()
	mock_settings.CURRENCY_SERVICE_URL = "http://currency:8001"
	mock_settings.SECURITY_SERVICE_URL = "http://security:8002"
	mock_settings.INTERNAL_API_KEY = "test-key"

	mock_container = MagicMock()
	mock_container.settings = mock_settings
	mock_container.session_factory = MagicMock()

	with (
		patch("transaction_service.core.uow.get_container", return_value=mock_container),
		patch("transaction_service.clients.currency.get_container", return_value=mock_container),
	):
		yield mock_container


@pytest.fixture
def mock_uow():
	"""Фикстура-заглушка Unit of Work для Transaction Service."""
	uow = MagicMock()
	uow.transactions = AsyncMock()
	uow.history_query = AsyncMock()
	uow.session = AsyncMock()

	# Мок контекстного менеджера
	uow.__aenter__ = AsyncMock(return_value=uow)
	uow.__aexit__ = AsyncMock(return_value=None)
	uow.commit = AsyncMock()
	uow.rollback = AsyncMock()
	uow.add_event = MagicMock()

	return uow
