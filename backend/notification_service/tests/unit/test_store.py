import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from notification_service.store import client


@pytest.fixture(autouse=True)
def reset_mongo_client_state():
    """Сброс глобального состояния клиента Mongo."""
    client._client = None
    client._db = None
    yield
    client._client = None
    client._db = None


@pytest.mark.asyncio
@patch("notification_service.store.client.AsyncIOMotorClient")
async def test_init_mongo_success(mock_motor):
    """Инициализация Mongo и создание индекса."""
    mock_cl = MagicMock()
    mock_motor.return_value = mock_cl
    mock_db = MagicMock()
    mock_cl.get_default_database.return_value = mock_db
    
    mock_coll = AsyncMock()
    mock_db.__getitem__.return_value = mock_coll
    
    from notification_service.store.client import init_mongo
    await init_mongo("mongodb://test:27017")
    
    assert client._client == mock_cl
    assert client._db == mock_db
    # Проверка создания индекса TTL
    mock_coll.create_index.assert_awaited_once_with("created_at", expireAfterSeconds=90 * 86_400)


@pytest.mark.asyncio
async def test_close_mongo_active():
    """Закрытие активного соединения Mongo."""
    mock_cl = MagicMock()
    client._client = mock_cl
    
    from notification_service.store.client import close_mongo
    await close_mongo()
    
    mock_cl.close.assert_called_once()
    assert client._client is None


@pytest.mark.asyncio
async def test_close_mongo_inactive():
    """Безопасное закрытие, если соединение не было открыто."""
    from notification_service.store.client import close_mongo
    await close_mongo() # No error
