from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from shared.config.base import BaseAppSettings
from shared.bootstrap import bootstrap, get_container

@pytest.fixture(autouse=True)
def reset_mongo_client_state():
    """Явная инициализация и сброс состояния контейнера для тестов."""
    bootstrap(BaseAppSettings)
    container = get_container()
    container._mongo_client = None
    container._mongo_db = None
    yield
    container._mongo_client = None
    container._mongo_db = None

@pytest.mark.asyncio
@patch("shared.mongodb_core.db.AsyncIOMotorClient")
async def test_init_mongodb_success(mock_motor):
    """Инициализация Mongo через shared.mongodb_core и проверка параметров."""
    mock_cl = MagicMock()
    mock_motor.return_value = mock_cl
    mock_db = MagicMock()
    mock_cl.get_default_database.return_value = mock_db
    mock_coll = AsyncMock()
    mock_db.__getitem__.return_value = mock_coll

    from shared.mongodb_core import init_mongodb
    
    mongo_indexes = [
        {
            "collection": "email_log",
            "fields": [("created_at", 1)],
            "expireAfterSeconds": 90 * 86_400,
        }
    ]

    await init_mongodb("mongodb://test:27017", indexes=mongo_indexes)

    container = get_container()
    assert container._mongo_client == mock_cl
    assert container._mongo_db == mock_db
    # Проверка создания индекса 
    mock_coll.create_index.assert_awaited_once_with([("created_at", 1)], expireAfterSeconds=90 * 86_400)

@pytest.mark.asyncio
async def test_close_mongodb_active():
    """Закрытие активного соединения Mongo через shared.mongodb_core."""
    mock_cl = MagicMock()
    container = get_container()
    container._mongo_client = mock_cl

    from shared.mongodb_core import close_mongodb
    await close_mongodb()

    mock_cl.close.assert_called_once()
    assert container._mongo_client is None
