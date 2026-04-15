from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from security_service.mongo_repository import SecurityEventRepository

@pytest.fixture
@patch("security_service.mongo_repository.get_mongodb")
def repo(mock_get_mongodb):
    """Фикстура репозитория с моком базы данных."""
    mock_db = MagicMock()
    mock_get_mongodb.return_value = mock_db
    mock_coll = AsyncMock()
    mock_db.__getitem__.return_value = mock_coll

    repository = SecurityEventRepository(collection_name="test_collection")
    repository.collection = mock_coll  # Для мока
    return repository

@pytest.mark.asyncio
async def test_repository_save_event_success(repo):
    """Успешное сохранение события безопасности."""
    await repo.save_event(
        account_id="acc-123",
        rule="large_transfer",
        details={"amount": "1000000"},
        action="block",
        threshold="500000",
        actual="1000000",
    )

    # Проверка вызова insert_one через правильную коллекцию
    repo.db["test_collection"].insert_one.assert_awaited_once()
    doc = repo.db["test_collection"].insert_one.call_args.args[0]
    
    assert doc["account_id"] == "acc-123"
    assert doc["rule"] == "large_transfer"
    assert doc["action"] == "block"
    assert "created_at" in doc

@pytest.mark.asyncio
async def test_repository_save_event_error_is_silenced(repo):
    """Ошибка вставки в Mongo не должна прерывать выполнение."""
    repo.db["test_collection"].insert_one.side_effect = Exception("Mongo error")

    # Не должно бросать исключение
    await repo.save_event(
        account_id="x", rule="y", details={}, action="z"
    )

    repo.db["test_collection"].insert_one.assert_awaited_once()
