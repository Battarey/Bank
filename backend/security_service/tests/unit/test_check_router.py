from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest

from security_service.api.antifraud import check_transaction


@pytest.mark.asyncio
@patch("security_service.api.antifraud.service.check_transaction")
async def test_check_transaction_api_success(mock_check, mock_mongo_repo, mock_uow):
	"""Роутер: успешный вызов проверки без нарушений."""
	account_id = uuid4()
	mock_check.return_value = []  # Нет нарушений

	# Имитируем запрос (SecurityCheckRequest)
	class MockPayload:
		def __init__(self):
			self.account_id = account_id
			self.tx_type = "deposit"
			self.amount = Decimal("100.00")
			self.currency = "RUB"

	res = await check_transaction(
		payload=MockPayload(),
		uow=mock_uow,
		mongo_repo=mock_mongo_repo,
	)

	assert res.allowed is True
	assert len(res.violations) == 0
	mock_check.assert_awaited_once()


@pytest.mark.asyncio
@patch("security_service.api.antifraud.service.check_transaction")
async def test_check_transaction_api_violation(mock_check, mock_mongo_repo, mock_uow):
	"""Роутер: вызов проверки с обнаруженными нарушениями."""
	from security_service.services.rules import Violation

	account_id = uuid4()
	mock_violation = Violation(rule="test_rule", threshold="100", actual="200", details={})
	mock_check.return_value = [mock_violation]

	class MockPayload:
		def __init__(self):
			self.account_id = account_id
			self.tx_type = "withdrawal"
			self.amount = Decimal("200.00")
			self.currency = "RUB"

	res = await check_transaction(
		payload=MockPayload(),
		uow=mock_uow,
		mongo_repo=mock_mongo_repo,
	)

	assert res.allowed is False
	assert len(res.violations) == 1
	assert res.violations[0].rule == "test_rule"
