import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from shared import models
from transaction_service.history.service import list_transactions
from transaction_service.exceptions import AccountNotFound


def _make_account(client_id=None):
    acc = models.BankAccount()
    acc.id = uuid4()
    acc.client_id = client_id or uuid4()
    return acc


@pytest.mark.asyncio
async def test_list_transactions_account_not_found(mock_session):
    mock_session.get.return_value = None
    with pytest.raises(AccountNotFound):
        await list_transactions(mock_session, uuid4(), uuid4())


@pytest.mark.asyncio
async def test_list_transactions_wrong_user(mock_session):
    acc = _make_account()
    mock_session.get.return_value = acc
    with pytest.raises(AccountNotFound):
        await list_transactions(mock_session, uuid4(), acc.id)


@pytest.mark.asyncio
async def test_list_transactions_success(mock_session):
    user_id = uuid4()
    acc = _make_account(client_id=user_id)
    mock_session.get.return_value = acc

    # count query
    count_result = MagicMock()
    count_result.scalar_one.return_value = 2

    # list query
    tx1 = models.Transaction()
    tx1.id = uuid4()
    tx2 = models.Transaction()
    tx2.id = uuid4()
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [tx1, tx2]

    mock_session.execute.side_effect = [count_result, list_result]

    txs, total = await list_transactions(mock_session, user_id, acc.id)
    assert total == 2
    assert len(txs) == 2


@pytest.mark.asyncio
async def test_list_transactions_with_filters(mock_session):
    user_id = uuid4()
    acc = _make_account(client_id=user_id)
    mock_session.get.return_value = acc

    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []
    mock_session.execute.side_effect = [count_result, list_result]

    txs, total = await list_transactions(mock_session, user_id, acc.id, tx_type="deposit", direction="incoming")
    assert total == 0
    assert txs == []
