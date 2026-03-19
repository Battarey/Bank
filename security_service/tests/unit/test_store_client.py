import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from security_service.store import client

@pytest.fixture(autouse=True)
def reset_globals():
    client._client = None
    client._db = None
    yield
    client._client = None
    client._db = None

@pytest.mark.asyncio
@patch("security_service.store.client.AsyncIOMotorClient")
async def test_init_close(mock_motor):
    mock_cl = MagicMock()
    mock_motor.return_value = mock_cl
    mock_db = MagicMock()
    mock_db.name = "test_db"
    mock_cl.get_default_database.return_value = mock_db
    mock_coll = AsyncMock()
    mock_db.__getitem__.return_value = mock_coll
    
    await client.init_mongo()
    
    assert client._client == mock_cl
    assert client._db == mock_db
    mock_coll.create_index.assert_awaited_once_with("created_at", expireAfterSeconds=365 * 86_400)
    
    await client.close_mongo()
    assert client._client is None
    assert client._db is None
    mock_cl.close.assert_called_once()

def test_get_db_error():
    with pytest.raises(RuntimeError, match="MongoDB не инициализирована"):
        client._get_db()

@pytest.mark.asyncio
@patch("security_service.store.client.datetime")
async def test_save_event(mock_dt):
    mock_db = MagicMock()
    client._db = mock_db
    
    mock_coll = AsyncMock()
    mock_db.__getitem__.return_value = mock_coll
    
    mock_now = MagicMock()
    mock_dt.now.return_value = mock_now
    
    await client.save_event(
        account_id="acc1",
        rule="rule1",
        details={"d": 1},
        action="freeze",
        threshold="t",
        actual="a"
    )
    
    mock_coll.insert_one.assert_awaited_once_with({
        "account_id": "acc1",
        "rule": "rule1",
        "details": {"d": 1},
        "action": "freeze",
        "threshold": "t",
        "actual": "a",
        "created_at": mock_now,
    })
