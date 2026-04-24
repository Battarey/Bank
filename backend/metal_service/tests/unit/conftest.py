import os
from unittest.mock import MagicMock, patch

import pytest

from metal_service.repositories.metal import MetalRepository

# Устанавливаем переменные окружения
os.environ.setdefault("METALS_DEV_API_KEY", "test-key")
os.environ.setdefault("METALS_DEV_BASE_URL", "https://api.test")
os.environ.setdefault("METAL_RATE_CACHE_TTL", "30")


@pytest.fixture(autouse=True)
def mock_bootstrap():
	"""Мокирование настроек."""
	mock_settings = MagicMock()
	mock_settings.METAL_RATE_CACHE_TTL = 30
	mock_settings.METALS_DEV_BASE_URL = "https://api.test"
	mock_settings.METALS_DEV_API_KEY = "test-key"

	mock_container = MagicMock()
	mock_container.settings = mock_settings

	with patch("metal_service.repositories.metal.get_container", return_value=mock_container):
		yield mock_container


@pytest.fixture
def metal_repository():
	"""Фикстура репозитория с очисткой кэша."""
	repo = MetalRepository()
	return repo
