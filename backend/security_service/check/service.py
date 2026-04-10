"""Бизнес-логика антифрод-проверки — оркестрация AML-правил."""

import logging
from decimal import Decimal
from uuid import UUID

from shared.events.base import LogEvent

from ..rules import ALL_RULES, Violation
from ..store import save_event
from ..uow import SecurityUnitOfWork

logger = logging.getLogger("security_service")


async def check_transaction(
	uow: SecurityUnitOfWork,
	account_id: UUID,
	tx_type: str,
	amount: Decimal,
	currency: str,
) -> list[Violation]:
	"""Проводит комплексную проверку транзакции по всем активным AML-правилам.

	Каждое нарушение логируется в MongoDB для последующего анализа.
	В случае срабатывания хотя бы одного правила, операция считается подозрительной.
	Регистрирует событие LogEvent в Unit of Work при обнаружении нарушений.

	Args:
		uow: Unit of Work для управления транзакцией и событиями.
		account_id: ID проверяемого счёта.
		tx_type: Тип операции (deposit, withdrawal, transfer, exchange).
		amount: Сумма операции.
		currency: Код валюты счёта.

	Returns:
		list[Violation]: Список зафиксированных нарушений (пустой, если проверка пройдена).
	"""
	violations: list[Violation] = []

	async with uow:
		# Проверка существования счёта
		await uow.accounts.get_account(account_id)

		for rule_fn in ALL_RULES:
			# Передаем session из UoW в правила
			violation = await rule_fn(uow.session, account_id, amount, currency)
			if violation is not None:
				violations.append(violation)

				# Фиксация события безопасности в MongoDB (внешнее хранилище)
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

			# Регистрация события безопасности «на вырост»
			uow.add_event(LogEvent(
				user_id=None, # Security-лог может быть не привязан к сессии пользователя
				action="aml_violation",
				service="security_service",
				details=f"Нарушения: {rules_summary}",
				entity_id=account_id,
				entity_type="bank_account",
				status="warning",
			))

		await uow.commit()

	return violations
