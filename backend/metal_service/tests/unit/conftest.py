import os
from unittest.mock import MagicMock, patch

import pytest

from metal_service.clients import metal_client

# Устанавливаем переменные окружения
os.environ.setdefault("METALS_DEV_API_KEY", "test-key")
os.environ.setdefault("METALS_DEV_BASE_URL", "https://api.test")
os.environ.setdefault("METAL_RATE_CACHE_TTL", "30")


@pytest.fixture(autouse=True)
def cleanup_and_mock_bootstrap():
	"""Сброс состояния и мокирование BootstrapContainer."""
	metal_client._client = None
	metal_client._cache.clear()

	mock_settings = MagicMock()
	mock_settings.METAL_RATE_CACHE_TTL = 30

	mock_container = MagicMock()
	mock_container.settings = mock_settings

	with patch("metal_service.clients.metal_client.get_container", return_value=mock_container):
		yield mock_container

	metal_client._client = None
	metal_client._cache.clear()
