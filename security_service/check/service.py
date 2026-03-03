"""Бизнес-логика антифрод-проверки — оркестрация AML-правил."""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from security_service.rules import ALL_RULES, Violation
from security_service.store import save_event

logger = logging.getLogger("security_service")


async def check_transaction(
	session: AsyncSession,
	account_id: UUID,
	tx_type: str,
	amount: Decimal,
	currency: str,
) -> list[Violation]:
	"""Проверяет pending-транзакцию по всем AML-правилам.

	Возвращает список сработавших правил (пустой = всё ок).
	Каждое срабатывание логируется в MongoDB.
	"""

	violations: list[Violation] = []

	for rule_fn in ALL_RULES:
		violation = await rule_fn(session, account_id, amount, currency)
		if violation is not None:
			violations.append(violation)

			# Логируем в MongoDB
			try:
				await save_event(
					account_id=str(account_id),
					rule=violation.rule,
					details={
						**violation.details,
						"tx_type": tx_type,
						"amount": str(amount),
						"currency": currency,
					},
					action="freeze",
					threshold=violation.threshold,
					actual=violation.actual,
				)
			except Exception:
				logger.exception(
					"Не удалось сохранить security event: rule=%s, account=%s",
					violation.rule, account_id,
				)

	if violations:
		rules = ", ".join(v.rule for v in violations)
		logger.warning(
			"AML violations: account=%s, tx_type=%s, amount=%s %s, rules=[%s]",
			account_id, tx_type, amount, currency, rules,
		)

	return violations
