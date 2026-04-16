"""Бизнес-логика антифрод-проверки — оркестрация AML-правил."""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from shared.bootstrap import get_container
from shared.events.base import LogEvent

from ..core.uow import SecurityUnitOfWork
from ..repositories.audit import SecurityEventRepository
from .rules import ALL_RULES, Violation

logger = logging.getLogger("security_service")


async def check_transaction(
	uow: SecurityUnitOfWork,
	mongo_repo: SecurityEventRepository,
	account_id: UUID,
	tx_type: str,
	amount: Decimal,
	currency: str,
) -> list[Violation]:
	"""Проводит комплексную проверку транзакции по всем активным AML-правилам.

	Сервис собирает необходимые агрегаты из БД через репозиторий и передает их
	в набор правил для анализа. Каждое нарушение фиксируется в MongoDB.

	Args:
		uow: Unit of Work для доступа к репозиторию и управлению транзакцией.
		mongo_repo: Репозиторий событий безопасности (MongoDB).
		account_id: ID проверяемого счёта.
		tx_type: Тип операции (deposit, withdrawal, transfer, exchange).
		amount: Сумма операции.
		currency: Код валюты счёта.

	Returns:
		list[Violation]: Список зафиксированных нарушений (пустой, если проверка пройдена).
	"""
	violations: list[Violation] = []
	settings = get_container().settings

	async with uow:
		# Проверка существования счёта
		await uow.accounts.get_account(account_id)

		# Подготовка данных для правил
		now = datetime.now(UTC)
		since_24h = now - timedelta(hours=24)
		since_rapid = now - timedelta(minutes=settings.RAPID_FIRE_WINDOW_MIN)

		# Собираем агрегаты один раз в рамках одной транзакции UoW
		data_context = {
			"total_today": await uow.accounts.get_total_amount_since(account_id, since_24h, direction="outgoing"),
			"count_today": await uow.accounts.get_transaction_count_since(account_id, since_24h, direction="outgoing"),
			"count_recent": await uow.accounts.get_transaction_count_since(account_id, since_rapid, direction="outgoing"),
			"structuring_hits": await uow.accounts.get_pattern_count(
				account_id,
				since_24h,
				lower_bound=settings.LARGE_TX_THRESHOLD * settings.STRUCTURING_RATIO,
				upper_bound=settings.LARGE_TX_THRESHOLD,
			),
			"round_hits": await uow.accounts.get_round_amount_count(
				account_id,
				since_24h,
				floor=settings.ROUND_AMOUNT_FLOOR,
				step=settings.ROUND_AMOUNT_STEP,
			),
		}

		# Запуск правил
		for rule_fn in ALL_RULES:
			# Передаем настройки и все собранные данные
			violation = rule_fn(
				amount=amount,
				currency=currency,
				settings=settings,
				**data_context,
			)

			if violation:
				violations.append(violation)

				# Фиксация события безопасности в MongoDB
				await mongo_repo.save_event(
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

		if violations:
			rules_summary = ", ".join(v.rule for v in violations)
			logger.warning(
				"AML Violation Detected: account=%s, type=%s, amount=%s %s, rules=[%s]",
				account_id,
				tx_type,
				amount,
				currency,
				rules_summary,
			)

			uow.add_event(
				LogEvent(
					user_id=None,
					action="aml_violation",
					service="security_service",
					details=f"Нарушения: {rules_summary}",
					entity_id=account_id,
					entity_type="bank_account",
					status="warning",
				)
			)

		await uow.commit()

	return violations
