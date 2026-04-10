from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from security_service.store import client


@pytest.fixture(autouse=True)
def reset_mongo_client_state():
    """Сброс глобального состояния клиента Mongo."""
    client._client = None
    client._db = None
    yield
    client._client = None
    client._db = None


@pytest.mark.asyncio
@patch("security_service.store.client.AsyncIOMotorClient")
async def test_init_mongo_success(mock_motor, mock_bootstrap):
    """Инициализация Mongo и создание индекса."""
    mock_cl = MagicMock()
    mock_motor.return_value = mock_cl
    mock_db = MagicMock()
    mock_cl.get_default_database.return_value = mock_db
    
    # Настройки
    mock_bootstrap.settings.MONGO_URL = "mongodb://test"
    mock_bootstrap.settings.SECURITY_COLLECTION = "events"
    mock_bootstrap.settings.SECURITY_TTL_DAYS = 365
    
    mock_coll = AsyncMock()
    mock_db.__getitem__.return_value = mock_coll
    
    from security_service.store.client import init_mongo
    await init_mongo()
    
    assert client._client == mock_cl
    assert client._db == mock_db
    # Проверка создания индекса TTL
    mock_coll.create_index.assert_awaited_once_with("created_at", expireAfterSeconds=365 * 86_400)


@pytest.mark.asyncio
async def test_close_mongo_active():
    """Закрытие активного соединения Mongo."""
    mock_cl = MagicMock()
    client._client = mock_cl
    
    from security_service.store.client import close_mongo
    await close_mongo()
    
    mock_cl.close.assert_called_once()
    assert client._client is None


@pytest.mark.asyncio
@patch("security_service.store.client.datetime")
async def test_save_event_success(mock_dt, mock_bootstrap):
    """Сохранение события безопасности в коллекцию."""
    mock_db = MagicMock()
    client._db = mock_db
    mock_coll = AsyncMock()
    mock_db.__getitem__.return_value = mock_coll
    
    mock_now = MagicMock()
    mock_dt.now.return_value = mock_now
    
    mock_bootstrap.settings.SECURITY_COLLECTION = "events"
    
    from security_service.store.client import save_event
    await save_event(
        account_id="acc1", rule="rule1", details={"d": 1}, action="freeze",
        threshold="t", actual="a"
    )
    
    mock_coll.insert_one.assert_awaited_once()
    doc = mock_coll.insert_one.call_args.args[0]
    assert doc["account_id"] == "acc1"
    assert doc["rule"] == "rule1"
    assert doc["created_at"] == mock_now
