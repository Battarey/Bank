from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from shared import mongodb_core

@pytest.fixture(autouse=True)
def reset_mongo_client_state():
    """Сброс глобального состояния клиента Mongo в shared подсистеме."""
    mongodb_core.db._client = None
    mongodb_core.db._db = None
    yield
    mongodb_core.db._client = None
    mongodb_core.db._db = None

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

    assert mongodb_core.db._client == mock_cl
    assert mongodb_core.db._db == mock_db
    # Проверка создания индекса 
    mock_coll.create_index.assert_awaited_once_with([("created_at", 1)], expireAfterSeconds=90 * 86_400)

@pytest.mark.asyncio
async def test_close_mongodb_active():
    """Закрытие активного соединения Mongo через shared.mongodb_core."""
    mock_cl = MagicMock()
    mongodb_core.db._client = mock_cl

    from shared.mongodb_core import close_mongodb
    await close_mongodb()

    mock_cl.close.assert_called_once()
    assert mongodb_core.db._client is None
