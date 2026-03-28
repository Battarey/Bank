import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4
from decimal import Decimal

from transaction_service import security_client


@pytest.fixture(autouse=True)
def reset_client():
    security_client._client = None
    yield
    security_client._client = None


@pytest.mark.asyncio
async def test_check_no_client():
    """Если клиент не инициализирован — fail-open (allowed=True)."""
    allowed, violations = await security_client.check_transaction(uuid4(), "withdrawal", Decimal("100"), "RUB")
    assert allowed is True
    assert violations == []


@pytest.mark.asyncio
async def test_check_allowed():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"allowed": True, "violations": []}
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    security_client._client = mock_client

    allowed, violations = await security_client.check_transaction(uuid4(), "transfer", Decimal("500"), "RUB")
    assert allowed is True
    assert violations == []


@pytest.mark.asyncio
async def test_check_denied():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"allowed": False, "violations": [{"rule": "rapid_fire"}]}
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    security_client._client = mock_client

    allowed, violations = await security_client.check_transaction(uuid4(), "transfer", Decimal("500"), "RUB")
    assert allowed is False
    assert violations[0]["rule"] == "rapid_fire"


@pytest.mark.asyncio
async def test_check_service_error():
    """При ошибке запроса — fail-open."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = Exception("timeout")
    security_client._client = mock_client

    allowed, violations = await security_client.check_transaction(uuid4(), "transfer", Decimal("500"), "RUB")
    assert allowed is True


@pytest.mark.asyncio
async def test_check_non_200():
    """При не-200 статусе — fail-open."""
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_resp.text = "Service Unavailable"
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    security_client._client = mock_client

    allowed, violations = await security_client.check_transaction(uuid4(), "deposit", Decimal("200"), "RUB")
    assert allowed is True
