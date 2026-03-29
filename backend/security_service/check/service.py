"""Бизнес-логика антифрод-проверки — оркестрация AML-правил."""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..rules import ALL_RULES, Violation
from ..store import save_event
from ..repository import SecurityRepository

logger = logging.getLogger("security_service")


async def check_transaction(
	session: AsyncSession,
	account_id: UUID,
	tx_type: str,
	amount: Decimal,
	currency: str,
) -> list[Violation]:
	"""Проводит комплексную проверку транзакции по всем активным AML-правилам.

	Каждое нарушение логируется в постоянное хранилище (MongoDB) для последующего анализа.
	В случае срабатывания хотя бы одного правила, операция считается подозрительной.

	Args:
		session: Сессия БД для доступа к истории транзакций.
		account_id: ID проверяемого счёта.
		tx_type: Тип операции (deposit, withdrawal, transfer).
		amount: Сумма операции в базовой валюте счёта.
		currency: Код валюты счёта.

	Returns:
		list[Violation]: Список зафиксированных нарушений (пустой, если проверка пройдена).
	"""
	violations: list[Violation] = []
	repo = SecurityRepository(session)
	
	# Проверка существования счёта
	await repo.get_account(account_id)

	for rule_fn in ALL_RULES:
		violation = await rule_fn(session, account_id, amount, currency)
		if violation is not None:
			violations.append(violation)

			# Фиксация события безопасности в MongoDB
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
					action="freeze", # Рекомендованное действие
					threshold=violation.threshold,
					actual=violation.actual,
				)
			except Exception:
				logger.exception(
					"Ошибка записи security event в хранилище: rule=%s, account=%s",
					violation.rule, account_id,
				)

	if violations:
		rules_summary = ", ".join(v.rule for v in violations)
		logger.warning(
			"AML Violation Detected: account=%s, type=%s, amount=%s %s, rules=[%s]",
			account_id, tx_type, amount, currency, rules_summary,
		)

	return violations
