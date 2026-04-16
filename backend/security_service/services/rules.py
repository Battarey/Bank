"""AML-правила для обнаружения подозрительных операций.

Каждое правило — чистая функция, принимающая необходимые данные и настройки.
Если правило срабатывает, оно возвращает объект Violation с подробным описанием ошибки.
Набор правил основан на рекомендациях ФСМ РФ и стандартах банковской безопасности.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from security_service.core.config import SecuritySettings


@dataclass(frozen=True, slots=True)
@runtime_checkable
class Violation:
	"""Зафиксированное нарушение AML-правила.

	Attributes:
		rule: Идентификатор сработавшего правила.
		threshold: Текстовое описание порога срабатывания.
		actual: Фактическое значение, вызвавшее срабатывание.
		details: Словарь с техническими деталями для инспектора.
	"""

	rule: str
	threshold: str
	actual: str
	details: dict[str, Any]


class RuleProtocol(Protocol):
	"""Протокол для AML-правил."""

	def __call__(
		self,
		*,
		amount: Decimal,
		currency: str,
		settings: SecuritySettings,
		**kwargs: Any,
	) -> Violation | None:
		...


def check_large_single_tx(
	*,
	amount: Decimal,
	currency: str,
	settings: SecuritySettings,
	**_kwargs: Any,
) -> Violation | None:
	"""Проверяет, не превышает ли разовая операция порог крупной сделки.

	Args:
		amount: Сумма текущей операции.
		currency: Код валюты операции.
		settings: Настройки сервиса безопасности.
		**_kwargs: Дополнительные данные (не используются в этом правиле).

	Returns:
		Violation | None: Описание нарушения или None, если проверка пройдена.
	"""
	if amount >= settings.LARGE_TX_THRESHOLD:
		return Violation(
			rule="large_single_tx",
			threshold=f"{settings.LARGE_TX_THRESHOLD} {currency}",
			actual=f"{amount} {currency}",
			details={
				"description": "Крупная разовая операция",
				"amount": str(amount),
				"threshold": str(settings.LARGE_TX_THRESHOLD),
			},
		)
	return None


def check_daily_amount_limit(
	*,
	amount: Decimal,
	currency: str,
	settings: SecuritySettings,
	total_today: Decimal,
	**_kwargs: Any,
) -> Violation | None:
	"""Проверяет суммарный объём операций по счёту за последние 24 часа.

	Args:
		amount: Сумма новой (pending) операции.
		currency: Код валюты операции.
		settings: Настройки сервиса безопасности.
		total_today: Текущая сумма успешных транзакций за 24ч.
		**_kwargs: Дополнительные данные.

	Returns:
		Violation | None: Описание нарушения или None.
	"""
	projected = total_today + amount

	if projected >= settings.DAILY_AMOUNT_LIMIT:
		return Violation(
			rule="daily_amount_limit",
			threshold=f"{settings.DAILY_AMOUNT_LIMIT} {currency}",
			actual=f"{projected} {currency}",
			details={
				"description": "Суммарный объём за 24 ч превышает лимит",
				"total_today": str(total_today),
				"pending": str(amount),
				"projected": str(projected),
			},
		)
	return None


def check_daily_count_limit(
	*,
	settings: SecuritySettings,
	count_today: int,
	**_kwargs: Any,
) -> Violation | None:
	"""Проверяет количество операций по счёту за последние 24 часа.

	Args:
		settings: Настройки сервиса безопасности.
		count_today: Текущее количество завершенных транзакций за 24ч.
		**_kwargs: Дополнительные данные.

	Returns:
		Violation | None: Описание нарушения или None.
	"""
	projected = count_today + 1

	if projected > settings.DAILY_TX_COUNT:
		return Violation(
			rule="daily_count_limit",
			threshold=str(settings.DAILY_TX_COUNT),
			actual=str(projected),
			details={
				"description": "Количество операций за 24 ч превышает лимит",
				"count_today": count_today,
				"projected": projected,
			},
		)
	return None


def check_rapid_fire(
	*,
	settings: SecuritySettings,
	count_recent: int,
	**_kwargs: Any,
) -> Violation | None:
	"""Выявляет серию операций за аномально короткий период времени (rapid-fire).

	Args:
		settings: Настройки сервиса безопасности.
		count_recent: Данные из репозитория: кол-во транзакций за короткое окно.
		**_kwargs: Дополнительные данные.

	Returns:
		Violation | None: Описание нарушения или None.
	"""
	projected = count_recent + 1

	if projected > settings.RAPID_FIRE_COUNT:
		return Violation(
			rule="rapid_fire",
			threshold=f"{settings.RAPID_FIRE_COUNT} за {settings.RAPID_FIRE_WINDOW_MIN} мин",
			actual=str(projected),
			details={
				"description": "Слишком частые операции (rapid-fire)",
				"window_minutes": settings.RAPID_FIRE_WINDOW_MIN,
				"count_in_window": count_recent,
				"projected": projected,
			},
		)
	return None


def check_structuring(
	*,
	amount: Decimal,
	settings: SecuritySettings,
	structuring_hits: int,
	**_kwargs: Any,
) -> Violation | None:
	"""Выявляет признаки дробления транзакций (structuring).

	Args:
		amount: Сумма операции.
		settings: Настройки сервиса безопасности.
		structuring_hits: Кол-во уже зафиксированных транзакций в подозрительном диапазоне.
		**_kwargs: Дополнительные данные.

	Returns:
		Violation | None: Описание нарушения или None.
	"""
	lower_bound = settings.LARGE_TX_THRESHOLD * settings.STRUCTURING_RATIO
	upper_bound = settings.LARGE_TX_THRESHOLD

	# Учитываем текущую операцию
	current_is_suspicious = lower_bound <= amount < upper_bound
	total_hits = structuring_hits + (1 if current_is_suspicious else 0)

	if total_hits >= settings.STRUCTURING_MIN_HITS:
		return Violation(
			rule="structuring",
			threshold=f"{settings.STRUCTURING_MIN_HITS} операций в диапазоне [{lower_bound}–{upper_bound})",
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


def check_round_amount_pattern(
	*,
	amount: Decimal,
	settings: SecuritySettings,
	round_hits: int,
	**_kwargs: Any,
) -> Violation | None:
	"""Выявляет серийные крупные переводы круглыми суммами.

	Args:
		amount: Сумма операции.
		settings: Настройки сервиса безопасности.
		round_hits: Кол-во уже зафиксированных круглых операций за период.
		**_kwargs: Дополнительные данные.

	Returns:
		Violation | None: Описание нарушения или None.
	"""
	current_is_round = amount >= settings.ROUND_AMOUNT_FLOOR and amount % settings.ROUND_AMOUNT_STEP == 0
	total_hits = round_hits + (1 if current_is_round else 0)

	if total_hits >= settings.ROUND_AMOUNT_MIN_HITS:
		return Violation(
			rule="round_amount_pattern",
			threshold=f"{settings.ROUND_AMOUNT_MIN_HITS} круглых операций ≥{settings.ROUND_AMOUNT_FLOOR}",
			actual=str(total_hits),
			details={
				"description": "Серия крупных переводов круглыми суммами",
				"floor": str(settings.ROUND_AMOUNT_FLOOR),
				"step": str(settings.ROUND_AMOUNT_STEP),
				"hits_today": hits_today,
				"current_is_round": current_is_round,
			},
		)
	return None


# ── Реестр правил ──────────────────────────────────────────────────────

# Словарь правил: ключ - название параметра для данных из репозитория
ALL_RULES: list[RuleProtocol] = [
	check_large_single_tx,
	check_daily_amount_limit,
	check_daily_count_limit,
	check_rapid_fire,
	check_structuring,
	check_round_amount_pattern,
]

__all__ = [
	"ALL_RULES",
	"RuleProtocol",
	"Violation",
	"check_daily_amount_limit",
	"check_daily_count_limit",
	"check_large_single_tx",
	"check_rapid_fire",
	"check_round_amount_pattern",
	"check_structuring",
]
