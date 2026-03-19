import pytest
from unittest.mock import AsyncMock, patch
from decimal import Decimal
from uuid import uuid4

from security_service.check.router import check, SecurityCheckRequest
from security_service.rules import Violation

@pytest.mark.asyncio
@patch("security_service.check.router.service.check_transaction")
async def test_check_allowed(mock_check):
    mock_check.return_value = []
    
    session = AsyncMock()
    req = SecurityCheckRequest.model_validate({
        "account_id": str(uuid4()),
        "tx_type": "transfer",
        "amount": "500",
        "currency": "RUB"
    })
    
    res = await check(payload=req, session=session)
    assert res.allowed is True
    assert len(res.violations) == 0
    mock_check.assert_awaited_once()

@pytest.mark.asyncio
@patch("security_service.check.router.service.check_transaction")
async def test_check_denied(mock_check):
    mock_violation = Violation(
        rule="rapid_fire",
        threshold="5",
        actual="6",
        details={}
    )
    mock_check.return_value = [mock_violation]
    
    session = AsyncMock()
    req = SecurityCheckRequest.model_validate({
        "account_id": str(uuid4()),
        "tx_type": "transfer",
        "amount": "500",
        "currency": "RUB"
    })
    
    res = await check(payload=req, session=session)
    assert res.allowed is False
    assert len(res.violations) == 1
    assert res.violations[0].rule == "rapid_fire"
    assert res.violations[0].actual == "6"
    assert res.violations[0].threshold == "5"
