from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from notification_service.repository import NotificationRepository


@pytest.fixture
@patch("notification_service.repository.get_mongo")
def repo(mock_get_mongo):
    """Фикстура репозитория с моком базы данных."""
    mock_db = MagicMock()
    mock_get_mongo.return_value = mock_db
    mock_coll = AsyncMock()
    mock_db.__getitem__.return_value = mock_coll
    
    repository = NotificationRepository()
    repository.collection = mock_coll # Для удобства обращений в тестах
    return repository


@pytest.mark.asyncio
async def test_repository_save_success(repo):
    """Успешное сохранение уведомления."""
    await repo.save(
        msg_type="welcome",
        to="user@test.com",
        subject="Subj",
        body="Body",
        variables={"v": 1},
        status="sent"
    )
    
    repo.collection.insert_one.assert_awaited_once()
    doc = repo.collection.insert_one.call_args.args[0]
    assert doc["type"] == "welcome"
    assert doc["status"] == "sent"
    assert doc["to"] == "user@test.com"
    assert "created_at" in doc


@pytest.mark.asyncio
async def test_repository_save_error_is_silenced(repo):
    """Ошибка вставки в Mongo не должна всплывать выше репозитория."""
    repo.collection.insert_one.side_effect = Exception("DB error")
    
    # Не должно бросать исключение
    await repo.save(
        msg_type="test", to="a@b.com", subject="", body="",
        variables={}, status="failed"
    )
    
    repo.collection.insert_one.assert_awaited_once()
