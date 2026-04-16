from decimal import Decimal
from uuid import uuid4

import pytest

from security_service.core.config import SecuritySettings
from security_service.services.rules import (
	check_daily_amount_limit,
	check_daily_count_limit,
	check_large_single_tx,
	check_rapid_fire,
	check_round_amount_pattern,
	check_structuring,
)


@pytest.fixture
def settings():
	"""Фикстура для настроек безопасности с значениями по умолчанию."""
	return SecuritySettings()


def test_check_large_single_tx_triggered(settings):
	"""Правило: крупная разовая операция (>600к) — срабатывает."""
	violation = check_large_single_tx(
		amount=Decimal("700000"),
		currency="RUB",
		settings=settings
	)

	assert violation is not None
	assert violation.rule == "large_single_tx"
	assert "700000" in violation.actual


def test_check_large_single_tx_fine(settings):
	"""Правило: крупная разовая операция — не срабатывает для малых сумм."""
	violation = check_large_single_tx(
		amount=Decimal("100.00"),
		currency="RUB",
		settings=settings
	)
	assert violation is None


def test_check_daily_amount_limit_triggered(settings):
	"""Правило: дневной лимит — срабатывает."""
	violation = check_daily_amount_limit(
		amount=Decimal("200000"),
		currency="RUB",
		settings=settings,
		total_today=Decimal("900000")  # Сумма в базе
	)

	assert violation is not None
	assert violation.rule == "daily_amount_limit"
	assert "1100000" in violation.actual


def test_check_daily_count_limit_triggered(settings):
	"""Правило: лимит количества операций — срабатывает."""
	violation = check_daily_count_limit(
		settings=settings,
		count_today=20,  # Уже 20, текущая +1 = 21 (порог 20)
		amount=Decimal("100"),
		currency="RUB"
	)

	assert violation is not None
	assert violation.rule == "daily_count_limit"
	assert violation.actual == "21"


def test_check_rapid_fire_triggered(settings):
	"""Правило: частые операции (rapid-fire) — срабатывает."""
	violation = check_rapid_fire(
		settings=settings,
		count_recent=5,  # Уже 5 за окно, +1 = 6 (порог 5)
		amount=Decimal("100"),
		currency="RUB"
	)

	assert violation is not None
	assert violation.rule == "rapid_fire"
	assert violation.actual == "6"


def test_check_structuring_triggered(settings):
	"""Правило: дробление (structuring) — срабатывает."""
	# LARGE_TX_THRESHOLD = 600000, суммарно 3+ операции в диапазоне [540к, 600к)
	violation = check_structuring(
		amount=Decimal("550000"),
		settings=settings,
		structuring_hits=2,  # Уже было 2 попадания в базе
		currency="RUB"
	)

	assert violation is not None
	assert violation.rule == "structuring"
	assert violation.actual == "3"


def test_check_round_amount_triggered(settings):
	"""Правило: серия круглых сумм — срабатывает."""
	# По умолчанию: floor=100k, step=10k, min_hits=3
	violation = check_round_amount_pattern(
		amount=Decimal("200000"),
		settings=settings,
		round_hits=2,  # Уже 2 в базе
		currency="RUB"
	)

	assert violation is not None
	assert violation.rule == "round_amount_pattern"
	assert violation.actual == "3"
