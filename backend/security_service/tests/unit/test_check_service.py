from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from security_service.check.service import check_transaction
from security_service.rules import Violation


@pytest.mark.asyncio
async def test_check_transaction_no_violations(mock_mongo_repo, mock_uow):
	"""Сценарий: проверка пройдена — нарушения не найдены, события не создаются."""
	account_id = uuid4()

	# ALL_RULES: list[Any] = [check_large_single_tx, ...]
	# Patch all rules to return None
	with patch("security_service.check.service.ALL_RULES", []):
		violations = await check_transaction(
			mock_uow,
			mongo_repo=mock_mongo_repo,
			account_id=account_id,
			tx_type="deposit",
			amount=Decimal("100.00"),
			currency="RUB",
		)

		assert len(violations) == 0
		mock_uow.accounts.get_account.assert_awaited_once_with(account_id)
		mock_mongo_repo.save_event.assert_not_called()
		mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_transaction_with_violations(mock_mongo_repo, mock_uow):
	"""Сценарий: обнаружено нарушение — сохранение в Mongo и регистрация LogEvent."""
	account_id = uuid4()
	mock_violation = Violation(rule="test_rule", threshold="100", actual="200", details={"info": "x"})

	# Мокируем правила, чтобы одно сработало
	mock_rule = AsyncMock(return_value=mock_violation)

	with patch("security_service.check.service.ALL_RULES", [mock_rule]):
		violations = await check_transaction(
			mock_uow,
			mongo_repo=mock_mongo_repo,
			account_id=account_id,
			tx_type="withdrawal",
			amount=Decimal("200.00"),
			currency="RUB",
		)

		assert len(violations) == 1
		assert violations[0].rule == "test_rule"

		# Проверка сохранения в MongoDB
		mock_mongo_repo.save_event.assert_awaited_once()
		call_kwargs = mock_mongo_repo.save_event.call_args.kwargs
		assert call_kwargs["account_id"] == str(account_id)
		assert call_kwargs["rule"] == "test_rule"

		# Проверка регистрации события LogEvent в UoW
		mock_uow.add_event.assert_called_once()
		event = mock_uow.add_event.call_args.args[0]
		assert event.action == "aml_violation"
		assert event.entity_id == account_id

		mock_uow.commit.assert_awaited_once()
