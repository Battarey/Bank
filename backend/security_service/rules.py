"""AML-правила для обнаружения подозрительных операций.

Каждое правило — async-функция, которая принимает (session, account_id, amount, currency)
и возвращает Violation | None.

Пороговые значения берутся из переменных окружения с разумными дефолтами.

Правила:
1. large_single_tx        — Крупная разовая операция (≥ 600 000 ₽ по ФМ РФ)
2. daily_amount_limit      — Суммарный объём за 24ч превышает порог
3. daily_count_limit       — Количество операций за 24ч превышает порог
4. rapid_fire              — Слишком много операций за короткий период
5. structuring             — Дробление: несколько операций чуть ниже порога крупной
6. round_amount_pattern    — Серия крупных переводов круглыми суммами
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models


# ── Конфигурация (env → defaults) ──────────────────────────────────────

LARGE_TX_THRESHOLD = Decimal(os.getenv("LARGE_TX_THRESHOLD", "600000"))
DAILY_AMOUNT_LIMIT = Decimal(os.getenv("DAILY_AMOUNT_LIMIT", "1000000"))
DAILY_TX_COUNT = int(os.getenv("DAILY_TX_COUNT", "20"))
RAPID_FIRE_COUNT = int(os.getenv("RAPID_FIRE_COUNT", "5"))
RAPID_FIRE_WINDOW_MIN = int(os.getenv("RAPID_FIRE_WINDOW_MIN", "3"))
STRUCTURING_RATIO = Decimal(os.getenv("STRUCTURING_RATIO", "0.9"))
STRUCTURING_MIN_HITS = int(os.getenv("STRUCTURING_MIN_HITS", "3"))
ROUND_AMOUNT_FLOOR = Decimal(os.getenv("ROUND_AMOUNT_FLOOR", "100000"))
ROUND_AMOUNT_STEP = Decimal(os.getenv("ROUND_AMOUNT_STEP", "10000"))
ROUND_AMOUNT_MIN_HITS = int(os.getenv("ROUND_AMOUNT_MIN_HITS", "3"))


# ── Результат проверки ─────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class Violation:
	"""Зафиксированное нарушение AML-правила."""

	rule: str
	threshold: str
	actual: str
	details: dict


# ── Правило 1: Крупная разовая операция ────────────────────────────────

async def check_large_single_tx(
	session: AsyncSession,
	account_id: UUID,
	amount: Decimal,
	currency: str,
) -> Violation | None:
	"""Проверяет, не превышает ли разовая операция порог крупной сделки."""

	if amount >= LARGE_TX_THRESHOLD:
		return Violation(
			rule="large_single_tx",
			threshold=f"{LARGE_TX_THRESHOLD} {currency}",
			actual=f"{amount} {currency}",
			details={
				"description": "Крупная разовая операция",
				"amount": str(amount),
				"threshold": str(LARGE_TX_THRESHOLD),
			},
		)
	return None


# ── Правило 2: Лимит суммы за сутки ───────────────────────────────────

async def check_daily_amount(
	session: AsyncSession,
	account_id: UUID,
	amount: Decimal,
	currency: str,
) -> Violation | None:
	"""Суммарный объём операций по счёту за 24 ч + текущая > порога."""

	since = datetime.now(UTC) - timedelta(hours=24)
	stmt = (
		select(func.coalesce(func.sum(models.Transaction.amount), 0))
		.where(
			models.Transaction.account_id == account_id,
			models.Transaction.created_at >= since,
		)
	)
	result = await session.execute(stmt)
	total_today = result.scalar()
	projected = Decimal(str(total_today)) + amount

	if projected >= DAILY_AMOUNT_LIMIT:
		return Violation(
			rule="daily_amount_limit",
			threshold=f"{DAILY_AMOUNT_LIMIT} {currency}",
			actual=f"{projected} {currency}",
			details={
				"description": "Суммарный объём за 24 ч превышает лимит",
				"total_today": str(total_today),
				"pending": str(amount),
				"projected": str(projected),
			},
		)
	return None


# ── Правило 3: Лимит количества за сутки ──────────────────────────────

async def check_daily_count(
	session: AsyncSession,
	account_id: UUID,
	amount: Decimal,
	currency: str,
) -> Violation | None:
	"""Количество операций по счёту за 24 ч + 1 > порога."""

	since = datetime.now(UTC) - timedelta(hours=24)
	stmt = (
		select(func.count())
		.select_from(models.Transaction)
		.where(
			models.Transaction.account_id == account_id,
			models.Transaction.created_at >= since,
		)
	)
	result = await session.execute(stmt)
	count_today = result.scalar()
	projected = count_today + 1

	if projected > DAILY_TX_COUNT:
		return Violation(
			rule="daily_count_limit",
			threshold=str(DAILY_TX_COUNT),
			actual=str(projected),
			details={
				"description": "Количество операций за 24 ч превышает лимит",
				"count_today": count_today,
				"projected": projected,
			},
		)
	return None


# ── Правило 4: Rapid-fire ─────────────────────────────────────────────

async def check_rapid_fire(
	session: AsyncSession,
	account_id: UUID,
	amount: Decimal,
	currency: str,
) -> Violation | None:
	"""Более N операций за последние M минут."""

	since = datetime.now(UTC) - timedelta(minutes=RAPID_FIRE_WINDOW_MIN)
	stmt = (
		select(func.count())
		.select_from(models.Transaction)
		.where(
			models.Transaction.account_id == account_id,
			models.Transaction.created_at >= since,
		)
	)
	result = await session.execute(stmt)
	count_recent = result.scalar()
	projected = count_recent + 1

	if projected > RAPID_FIRE_COUNT:
		return Violation(
			rule="rapid_fire",
			threshold=f"{RAPID_FIRE_COUNT} за {RAPID_FIRE_WINDOW_MIN} мин",
			actual=str(projected),
			details={
				"description": "Слишком частые операции",
				"window_minutes": RAPID_FIRE_WINDOW_MIN,
				"count_in_window": count_recent,
				"projected": projected,
			},
		)
	return None


# ── Правило 5: Structuring (дробление) ────────────────────────────────

async def check_structuring(
	session: AsyncSession,
	account_id: UUID,
	amount: Decimal,
	currency: str,
) -> Violation | None:
	"""Несколько операций в диапазоне [порог×0.9, порог) за 24 ч — признак дробления."""

	lower_bound = LARGE_TX_THRESHOLD * STRUCTURING_RATIO
	upper_bound = LARGE_TX_THRESHOLD
	since = datetime.now(UTC) - timedelta(hours=24)

	# Считаем текущую операцию
	current_is_suspicious = lower_bound <= amount < upper_bound

	stmt = (
		select(func.count())
		.select_from(models.Transaction)
		.where(
			models.Transaction.account_id == account_id,
			models.Transaction.created_at >= since,
			models.Transaction.amount >= lower_bound,
			models.Transaction.amount < upper_bound,
		)
	)
	result = await session.execute(stmt)
	hits_today = result.scalar()

	total_hits = hits_today + (1 if current_is_suspicious else 0)

	if total_hits >= STRUCTURING_MIN_HITS:
		return Violation(
			rule="structuring",
			threshold=f"{STRUCTURING_MIN_HITS} операций в диапазоне [{lower_bound}–{upper_bound})",
			actual=str(total_hits),
			details={
				"description": "Подозрение на дробление (structuring)",
				"range_low": str(lower_bound),
				"range_high": str(upper_bound),
				"hits_today": hits_today,
				"current_is_suspicious": current_is_suspicious,
			},
		)
	return None


# ── Правило 6: Round-amount pattern ───────────────────────────────────

async def check_round_amount(
	session: AsyncSession,
	account_id: UUID,
	amount: Decimal,
	currency: str,
) -> Violation | None:
	"""Серия крупных переводов круглыми суммами за 24 ч."""

	since = datetime.now(UTC) - timedelta(hours=24)
	current_is_round = (
		amount >= ROUND_AMOUNT_FLOOR
		and amount % ROUND_AMOUNT_STEP == 0
	)

	# Подсчёт: крупные операции с круглой суммой за последние 24 ч
	# amount % step == 0  →  amount - floor(amount / step) * step == 0
	# В SQL: amount::numeric % step = 0  (PostgreSQL поддерживает mod для numeric)
	stmt = (
		select(func.count())
		.select_from(models.Transaction)
		.where(
			models.Transaction.account_id == account_id,
			models.Transaction.created_at >= since,
			models.Transaction.amount >= ROUND_AMOUNT_FLOOR,
			models.Transaction.amount % ROUND_AMOUNT_STEP == 0,
		)
	)
	result = await session.execute(stmt)
	hits_today = result.scalar()

	total_hits = hits_today + (1 if current_is_round else 0)

	if total_hits >= ROUND_AMOUNT_MIN_HITS:
		return Violation(
			rule="round_amount_pattern",
			threshold=f"{ROUND_AMOUNT_MIN_HITS} круглых операций ≥{ROUND_AMOUNT_FLOOR}",
			actual=str(total_hits),
			details={
				"description": "Серия крупных переводов круглыми суммами",
				"floor": str(ROUND_AMOUNT_FLOOR),
				"step": str(ROUND_AMOUNT_STEP),
				"hits_today": hits_today,
				"current_is_round": current_is_round,
			},
		)
	return None


# ── Реестр правил ──────────────────────────────────────────────────────

ALL_RULES = [
	check_large_single_tx,
	check_daily_amount,
	check_daily_count,
	check_rapid_fire,
	check_structuring,
	check_round_amount,
]

__all__ = [
	"ALL_RULES",
	"Violation",
	"check_daily_amount",
	"check_daily_count",
	"check_large_single_tx",
	"check_rapid_fire",
	"check_round_amount",
	"check_structuring",
]
