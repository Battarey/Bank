from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from security_service.services.rules import (
	check_daily_amount,
	check_daily_count,
	check_large_single_tx,
	check_rapid_fire,
	check_round_amount,
	check_structuring,
)


@pytest.mark.asyncio
async def test_check_large_single_tx_triggered(mock_session):
	"""Правило: крупная разовая операция (>600к) — срабатывает."""
	account_id = uuid4()
	violation = await check_large_single_tx(mock_session, account_id, Decimal("700000"), "RUB")

	assert violation is not None
	assert violation.rule == "large_single_tx"
	assert "700000" in violation.actual


@pytest.mark.asyncio
async def test_check_large_single_tx_fine(mock_session):
	"""Правило: крупная разовая операция — не срабатывает для малых сумм."""
	account_id = uuid4()
	violation = await check_large_single_tx(mock_session, account_id, Decimal("100.00"), "RUB")
	assert violation is None


@pytest.mark.asyncio
async def test_check_daily_amount_triggered(mock_session):
	"""Правило: дневной лимит (>1млн) — срабатывает."""
	account_id = uuid4()
	# Mock result of sum(amount)
	mock_result = MagicMock()
	mock_result.scalar.return_value = Decimal("900000")
	mock_session.execute = AsyncMock(return_value=mock_result)

	violation = await check_daily_amount(mock_session, account_id, Decimal("200000"), "RUB")

	assert violation is not None
	assert violation.rule == "daily_amount_limit"
	assert "1100000" in violation.actual


@pytest.mark.asyncio
async def test_check_daily_count_triggered(mock_session):
	"""Правило: лимит количества операций (>20 за 24ч) — срабатывает."""
	account_id = uuid4()
	# Mock result of count()
	mock_result = MagicMock()
	mock_result.scalar.return_value = 20  # Already 20, now +1 = 21
	mock_session.execute = AsyncMock(return_value=mock_result)

	violation = await check_daily_count(mock_session, account_id, Decimal("100"), "RUB")

	assert violation is not None
	assert violation.rule == "daily_count_limit"
	assert violation.actual == "21"


@pytest.mark.asyncio
async def test_check_rapid_fire_triggered(mock_session):
	"""Правило: частые операции (>5 за 3мин) — срабатывает."""
	account_id = uuid4()
	mock_result = MagicMock()
	mock_result.scalar.return_value = 5  # +1 = 6
	mock_session.execute = AsyncMock(return_value=mock_result)

	violation = await check_rapid_fire(mock_session, account_id, Decimal("100"), "RUB")

	assert violation is not None
	assert violation.rule == "rapid_fire"
	assert violation.actual == "6"


@pytest.mark.asyncio
async def test_check_structuring_triggered(mock_session):
	"""Правило: дробление (structuring) — срабатывает (3+ операции в диапазоне 90-100% лимита)."""
	account_id = uuid4()
	# LARGE_TX_THRESHOLD = 600000, 90% = 540000
	mock_result = MagicMock()
	mock_result.scalar.return_value = 2  # Already 2 in DB
	mock_session.execute = AsyncMock(return_value=mock_result)

	# Current transaction is 550000 (suspicious)
	violation = await check_structuring(mock_session, account_id, Decimal("550000"), "RUB")

	assert violation is not None
	assert violation.rule == "structuring"
	assert violation.actual == "3"


@pytest.mark.asyncio
async def test_check_round_amount_triggered(mock_session):
	"""Правило: серия круглых сумм — срабатывает."""
	account_id = uuid4()
	mock_result = MagicMock()
	mock_result.scalar.return_value = 2  # Already 2 in DB
	mock_session.execute = AsyncMock(return_value=mock_result)

	# Large and round: 200000 (>=100k floor and div-able by 10k step)
	violation = await check_round_amount(mock_session, account_id, Decimal("200000"), "RUB")

	assert violation is not None
	assert violation.rule == "round_amount_pattern"
	assert violation.actual == "3"
