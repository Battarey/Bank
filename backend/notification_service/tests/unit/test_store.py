import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from notification_service.store import client


@pytest.fixture(autouse=True)
def reset_globals():
    client._client = None
    client._db = None
    yield
    client._client = None
    client._db = None


@pytest.mark.asyncio
@patch("notification_service.store.client.AsyncIOMotorClient")
async def test_init_mongo(mock_motor):
    mock_cl = MagicMock()
    mock_motor.return_value = mock_cl
    mock_db = MagicMock()
    mock_db.name = "test_db"
    mock_cl.get_default_database.return_value = mock_db
    mock_coll = AsyncMock()
    mock_db.__getitem__.return_value = mock_coll

    from notification_service.store.client import init_mongo
    await init_mongo()

    assert client._client == mock_cl
    assert client._db == mock_db
    mock_coll.create_index.assert_awaited_once_with(
        "created_at", expireAfterSeconds=90 * 86_400
    )


@pytest.mark.asyncio
async def test_close_mongo():
    mock_cl = MagicMock()
    client._client = mock_cl
    client._db = MagicMock()

    from notification_service.store.client import close_mongo
    await close_mongo()

    mock_cl.close.assert_called_once()
    assert client._client is None
    assert client._db is None


@pytest.mark.asyncio
async def test_close_mongo_not_connected():
    """Вызов close_mongo без init_mongo не кидает ошибок."""
    from notification_service.store.client import close_mongo
    await close_mongo()  # no error


def test_get_mongo_not_initialized():
    from notification_service.store.client import get_mongo
    with pytest.raises(RuntimeError, match="не инициализирована"):
        get_mongo()


def test_get_mongo_ok():
    mock_db = MagicMock()
    client._db = mock_db
    from notification_service.store.client import get_mongo
    db = get_mongo()
    assert db is mock_db


@pytest.mark.asyncio
@patch("notification_service.store.client.datetime")
async def test_save_notification(mock_dt):
    mock_db = MagicMock()
    client._db = mock_db
    mock_coll = AsyncMock()
    mock_db.__getitem__.return_value = mock_coll
    mock_now = MagicMock()
    mock_dt.now.return_value = mock_now

    from notification_service.store.client import save_notification
    await save_notification(
        msg_type="welcome",
        to="user@test.com",
        subject="Добро пожаловать!",
        body="Текст",
        variables={},
        status="sent",
    )

    mock_coll.insert_one.assert_awaited_once()
    doc = mock_coll.insert_one.call_args.args[0]
    assert doc["type"] == "welcome"
    assert doc["to"] == "user@test.com"
    assert doc["status"] == "sent"
    assert doc["error"] is None


@pytest.mark.asyncio
async def test_save_notification_with_error():
    mock_db = MagicMock()
    client._db = mock_db
    mock_coll = AsyncMock()
    mock_db.__getitem__.return_value = mock_coll

    from notification_service.store.client import save_notification
    await save_notification(
        msg_type="welcome",
        to="user@test.com",
        subject="",
        body="",
        variables={},
        status="failed",
        error="SMTP timeout",
    )

    doc = mock_coll.insert_one.call_args.args[0]
    assert doc["status"] == "failed"
    assert doc["error"] == "SMTP timeout"


@pytest.mark.asyncio
async def test_save_notification_mongo_error_silenced():
    """Ошибка MongoDB при save_notification перехватывается и не кидается наружу."""
    mock_db = MagicMock()
    client._db = mock_db
    mock_coll = AsyncMock()
    mock_coll.insert_one.side_effect = Exception("connection lost")
    mock_db.__getitem__.return_value = mock_coll

    from notification_service.store.client import save_notification
    # не кидает исключение
    await save_notification(
        msg_type="test", to="a@b.com", subject="", body="",
        variables={}, status="sent",
    )
