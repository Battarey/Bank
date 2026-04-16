from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from security_service.services.antifraud import check_transaction
from security_service.services.rules import Violation


@pytest.fixture
def mock_repo_aggregates(mock_uow):
	"""Настройка моков для методов агрегации репозитория."""
	mock_uow.accounts.get_total_amount_since = AsyncMock(return_value=Decimal("0"))
	mock_uow.accounts.get_transaction_count_since = AsyncMock(return_value=0)
	mock_uow.accounts.get_pattern_count = AsyncMock(return_value=0)
	mock_uow.accounts.get_round_amount_count = AsyncMock(return_value=0)
	return mock_uow.accounts


@pytest.mark.asyncio
async def test_check_transaction_no_violations(mock_mongo_repo, mock_uow, mock_repo_aggregates):
	"""Сценарий: проверка пройдена — нарушения не найдены."""
	account_id = uuid4()

	# Патчим реестр правил на пустой список
	with patch("security_service.services.antifraud.ALL_RULES", []):
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
		# Проверяем, что методы агрегации вызывались
		mock_uow.accounts.get_total_amount_since.assert_awaited_once()
		mock_mongo_repo.save_event.assert_not_called()
		mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_transaction_with_violations(mock_mongo_repo, mock_uow, mock_repo_aggregates):
	"""Сценарий: обнаружено нарушение — сохранение в Mongo и транзакция коммитится."""
	account_id = uuid4()
	mock_violation = Violation(rule="test_rule", threshold="100", actual="200", details={"info": "x"})

	# Мокируем правила (теперь они синхронные)
	mock_rule = MagicMock(return_value=mock_violation)

	with patch("security_service.services.antifraud.ALL_RULES", [mock_rule]):
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
		
		# Проверка регистрации события LogEvent в UoW
		mock_uow.add_event.assert_called_once()
		event = mock_uow.add_event.call_args.args[0]
		assert event.action == "aml_violation"
		assert event.entity_id == account_id

		mock_uow.commit.assert_awaited_once()
