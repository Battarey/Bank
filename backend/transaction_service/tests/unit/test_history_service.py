import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from transaction_service.history.service import list_transactions


@pytest.mark.asyncio
async def test_list_transactions_success(mock_uow):
    """Успешное получение истории транзакций."""
    user_id = uuid4()
    account_id = uuid4()
    
    mock_account = MagicMock()
    mock_account.client_id = user_id
    mock_uow.transactions.get_account.return_value = mock_account
    
    mock_tx = MagicMock()
    mock_uow.history_query.get_history_with_total.return_value = ([mock_tx], 1)
    
    # Вызов
    transactions, total = await list_transactions(
        uow=mock_uow,
        user_id=user_id,
        account_id=account_id,
        limit=10,
        offset=0
    )
    
    assert total == 1
    assert transactions[0] == mock_tx
    mock_uow.history_query.get_history_with_total.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_transactions_wrong_owner(mock_uow):
    """Ошибка: попытка посмотреть историю чужого счета."""
    user_id = uuid4()
    other_user_id = uuid4()
    account_id = uuid4()
    
    mock_account = MagicMock()
    mock_account.client_id = other_user_id
    mock_uow.transactions.get_account.return_value = mock_account
    
    from transaction_service.exceptions import AccountNotFound
    with pytest.raises(AccountNotFound):
        await list_transactions(mock_uow, user_id, account_id)
