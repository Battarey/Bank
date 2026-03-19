import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal
from uuid import uuid4

from security_service.check.service import check_transaction
from security_service.rules import Violation

@pytest.fixture
def mock_violation():
    return Violation(
        rule="test_rule",
        threshold="100",
        actual="101",
        details={"description": "test"}
    )

@pytest.mark.asyncio
@patch("security_service.check.service.ALL_RULES")
@patch("security_service.check.service.save_event")
async def test_check_transaction_no_violations(mock_save, mock_rules, mock_session):
    async def mock_rule_ok(*args, **kwargs):
        return None
    
    mock_rules.__iter__.return_value = [mock_rule_ok, mock_rule_ok]
    
    violations = await check_transaction(mock_session, uuid4(), "transfer", Decimal("100"), "RUB")
    
    assert len(violations) == 0
    mock_save.assert_not_awaited()

@pytest.mark.asyncio
@patch("security_service.check.service.ALL_RULES")
@patch("security_service.check.service.save_event")
async def test_check_transaction_with_violations(mock_save, mock_rules, mock_session, mock_violation):
    async def mock_rule_ok(*args, **kwargs):
        return None
    async def mock_rule_fail(*args, **kwargs):
        return mock_violation
    
    mock_rules.__iter__.return_value = [mock_rule_ok, mock_rule_fail, mock_rule_ok]
    
    acc_id = uuid4()
    violations = await check_transaction(mock_session, acc_id, "transfer", Decimal("100"), "RUB")
    
    assert len(violations) == 1
    assert violations[0] == mock_violation
    
    mock_save.assert_awaited_once_with(
        account_id=str(acc_id),
        rule=mock_violation.rule,
        details={
            **mock_violation.details,
            "tx_type": "transfer",
            "amount": "100",
            "currency": "RUB",
        },
        action="freeze",
        threshold=mock_violation.threshold,
        actual=mock_violation.actual,
    )

@pytest.mark.asyncio
@patch("security_service.check.service.logger")
@patch("security_service.check.service.ALL_RULES")
@patch("security_service.check.service.save_event")
async def test_check_transaction_save_error(mock_save, mock_rules, mock_logger, mock_session, mock_violation):
    async def mock_rule_fail(*args, **kwargs):
        return mock_violation
    
    mock_rules.__iter__.return_value = [mock_rule_fail]
    mock_save.side_effect = Exception("mongo error")
    
    acc_id = uuid4()
    violations = await check_transaction(mock_session, acc_id, "transfer", Decimal("100"), "RUB")
    
    assert len(violations) == 1
    mock_logger.exception.assert_called_once()
