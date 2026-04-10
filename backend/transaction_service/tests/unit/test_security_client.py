from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from transaction_service.security_client import check_transaction, connect, disconnect


@pytest.mark.asyncio
@patch("transaction_service.security_client.httpx.AsyncClient")
async def test_check_transaction_allowed(mock_client_cls, mock_bootstrap):
    """Антифрод: операция разрешена."""
    mock_client = AsyncMock()
    mock_client_cls.return_value = mock_client
    
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {"allowed": True, "violations": []}
    mock_client.post.return_value = mock_res
    
    await connect()
    allowed, violations = await check_transaction(uuid4(), "transfer", Decimal("500"), "RUB")
    
    assert allowed is True
    assert len(violations) == 0
    mock_client.post.assert_called_once()
    await disconnect()


@pytest.mark.asyncio
@patch("transaction_service.security_client.httpx.AsyncClient")
async def test_check_transaction_denied(mock_client_cls, mock_bootstrap):
    """Антифрод: операция заблокирована."""
    mock_client = AsyncMock()
    mock_client_cls.return_value = mock_client
    
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "allowed": False, 
        "violations": [{"rule": "test"}]
    }
    mock_client.post.return_value = mock_res
    
    await connect()
    allowed, violations = await check_transaction(uuid4(), "transfer", Decimal("1000000"), "RUB")
    
    assert allowed is False
    assert len(violations) == 1
    await disconnect()


@pytest.mark.asyncio
@patch("transaction_service.security_client.httpx.AsyncClient")
async def test_check_transaction_fail_open(mock_client_cls, mock_bootstrap):
    """Антифрод: сервис недоступен (fail-open)."""
    mock_client = AsyncMock()
    mock_client_cls.return_value = mock_client
    
    # 503 Service Unavailable
    mock_res = MagicMock()
    mock_res.status_code = 503
    mock_client.post.return_value = mock_res
    
    await connect()
    # При ошибке внешней системы возвращается (True, [])
    allowed, violations = await check_transaction(uuid4(), "deposit", Decimal("100"), "RUB")
    
    assert allowed is True
    assert len(violations) == 0
    await disconnect()
