"""Вспомогательные инструменты для transaction_service (DRY)."""

from datetime import UTC, datetime
from uuid import UUID

from shared import models
from shared.events.base import NotificationEvent

from .exceptions import AccountNotFound, SecurityViolation
from .uow import TransactionUnitOfWork


async def ensure_account_ownership(account: models.BankAccount, user_id: UUID) -> None:
	"""Проверяет принадлежность счета пользователю.

	Args:
		account: Объект банковского счета.
		user_id: ID пользователя для проверки.

	Raises:
		AccountNotFound: Если счет не принадлежит пользователю.
	"""
	if account.client_id != user_id:
		raise AccountNotFound("Счёт не принадлежит вам.")


async def apply_security_freeze(
	uow: TransactionUnitOfWork,
	account: models.BankAccount,
	violations: list[dict],
) -> None:
	"""Применяет системную заморозку счета при нарушении правил безопасности.

	Args:
		uow: Unit of Work для регистрации событий и фиксации состояния.
		account: Объект банковского счета для заморозки.
		violations: Список нарушенных правил от Security Service.

	Raises:
		SecurityViolation: Всегда выбрасывается после применения заморозки.
	"""
	reason = ", ".join(v["rule"] for v in violations)
	account.status = "frozen"
	account.frozen_by = "system"
	account.frozen_at = datetime.now(UTC)
	account.freeze_reason = f"AML: {reason}"

	uow.add_event(
		NotificationEvent(
			type="security_freeze",
			to="owner",
			variables={"account_number": account.account_number, "rule": reason},
		)
	)

	# Сохраняем состояние заморозки в БД немедленно
	await uow.commit()

	raise SecurityViolation(f"Операция отклонена безопасностью. Счёт заморожен: {reason}")
