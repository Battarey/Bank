from decimal import Decimal
from uuid import uuid4
from unittest.mock import MagicMock
import pytest

from security_service.rules import (
    Violation,
    check_large_single_tx,
    check_daily_amount,
    check_daily_count,
    check_rapid_fire,
    check_structuring,
    check_round_amount,
    LARGE_TX_THRESHOLD,
    DAILY_AMOUNT_LIMIT,
    DAILY_TX_COUNT,
    RAPID_FIRE_COUNT,
    STRUCTURING_MIN_HITS,
    ROUND_AMOUNT_FLOOR,
    ROUND_AMOUNT_STEP,
    ROUND_AMOUNT_MIN_HITS,
)

@pytest.mark.asyncio
async def test_large_single_tx():
    acc_id = uuid4()
    # Less than threshold
    res1 = await check_large_single_tx(None, acc_id, LARGE_TX_THRESHOLD - Decimal("1"), "RUB")
    assert res1 is None
    
    # Equals or greater
    res2 = await check_large_single_tx(None, acc_id, LARGE_TX_THRESHOLD, "RUB")
    assert isinstance(res2, Violation)
    assert res2.rule == "large_single_tx"

@pytest.mark.asyncio
async def test_daily_amount_limit(mock_session):
    acc_id = uuid4()
    
    # Under limit
    mock_result = MagicMock()
    mock_result.scalar.return_value = Decimal("500000")
    mock_session.execute.return_value = mock_result
    
    res1 = await check_daily_amount(mock_session, acc_id, Decimal("100000"), "RUB")
    assert res1 is None
    
    # Over limit
    res2 = await check_daily_amount(mock_session, acc_id, DAILY_AMOUNT_LIMIT - Decimal("100000"), "RUB")
    assert isinstance(res2, Violation)
    assert res2.rule == "daily_amount_limit"

@pytest.mark.asyncio
async def test_daily_count_limit(mock_session):
    acc_id = uuid4()
    
    # Under limit
    mock_result = MagicMock()
    mock_result.scalar.return_value = DAILY_TX_COUNT - 1
    mock_session.execute.return_value = mock_result
    
    res1 = await check_daily_count(mock_session, acc_id, Decimal("1"), "RUB")
    assert res1 is None
    
    # Over limit
    mock_result.scalar.return_value = DAILY_TX_COUNT
    res2 = await check_daily_count(mock_session, acc_id, Decimal("1"), "RUB")
    assert isinstance(res2, Violation)
    assert res2.rule == "daily_count_limit"

@pytest.mark.asyncio
async def test_rapid_fire(mock_session):
    acc_id = uuid4()
    
    mock_result = MagicMock()
    mock_result.scalar.return_value = RAPID_FIRE_COUNT - 1
    mock_session.execute.return_value = mock_result
    
    res1 = await check_rapid_fire(mock_session, acc_id, Decimal("1"), "RUB")
    assert res1 is None
    
    mock_result.scalar.return_value = RAPID_FIRE_COUNT
    res2 = await check_rapid_fire(mock_session, acc_id, Decimal("1"), "RUB")
    assert isinstance(res2, Violation)
    assert res2.rule == "rapid_fire"

@pytest.mark.asyncio
async def test_structuring(mock_session):
    acc_id = uuid4()
    
    mock_result = MagicMock()
    mock_result.scalar.return_value = STRUCTURING_MIN_HITS - 1
    mock_session.execute.return_value = mock_result
    
    # Under boundary sum -> current is NOT suspicious -> total hits = min_hits - 1
    res1 = await check_structuring(mock_session, acc_id, Decimal("100"), "RUB")
    assert res1 is None
    
    # Inside boundary sum -> current IS suspicious -> total hits = min_hits
    suspicious_amount = LARGE_TX_THRESHOLD * Decimal("0.95")
    res2 = await check_structuring(mock_session, acc_id, suspicious_amount, "RUB")
    assert isinstance(res2, Violation)
    assert res2.rule == "structuring"

@pytest.mark.asyncio
async def test_round_amount(mock_session):
    acc_id = uuid4()
    
    mock_result = MagicMock()
    mock_result.scalar.return_value = ROUND_AMOUNT_MIN_HITS - 1
    mock_session.execute.return_value = mock_result
    
    # Setup test logic boundary
    floor = ROUND_AMOUNT_FLOOR
    step = ROUND_AMOUNT_STEP
    
    # Non-round amount (> floor) -> Not round -> hit count = min_hits - 1
    res1 = await check_round_amount(mock_session, acc_id, floor + Decimal("1"), "RUB")
    assert res1 is None
    
    # Round amount (> floor) -> Round -> hit count = min_hits
    res2 = await check_round_amount(mock_session, acc_id, floor + step, "RUB")
    assert isinstance(res2, Violation)
    assert res2.rule == "round_amount_pattern"
