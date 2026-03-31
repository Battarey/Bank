from typing import Sequence
from uuid import UUID

from shared import models
from ..uow import TransactionUnitOfWork


async def list_transactions(
	uow: TransactionUnitOfWork,
	user_id: UUID,
	account_id: UUID,
	*,
	limit: int = 20,
	offset: int = 0,
	tx_type: str | None = None,
	direction: str | None = None,
) -> tuple[Sequence[models.Transaction], int]:
	"""Возвращает историю операций по счёту с поддержкой пагинации и фильтрации.

	Args:
		uow: Unit of Work для управления транзакцией.
		user_id: ID владельца счёта (для проверки прав).
		account_id: ID счёта, историю которого нужно получить.
		limit: Количество записей на страницу (макс. 100).
		offset: Смещение (пропуск записей).
		tx_type: Опциональный фильтр по типу (deposit, withdrawal, transfer).
		direction: Опциональный фильтр по направлению (incoming, outgoing).

	Returns:
		tuple[Sequence[Transaction], int]: Список транзакций и общее количество (total_count).
	"""
	async with uow:
		# 1. Проверка принадлежности счёта
		account = await uow.transactions.get_account(account_id)
		if account.client_id != user_id:
			from ..exceptions import AccountNotFound
			raise AccountNotFound("Счёт не принадлежит вам.")

		# 2. Получение данных через репозиторий
		return await uow.transactions.list_with_total(
			account_id,
			limit=limit,
			offset=offset,
			tx_type=tx_type,
			direction=direction,
		)


from shared.rabbitmq import send_notification


async def _notify_security_freeze(repo: TransactionRepository, user_id: UUID, account: models.BankAccount, rules: str) -> None:
	"""Вспомогательный метод для уведомления о блокировке AML (используется другими сервисами)."""
	contact = await repo.get_owner_contact(user_id)
	if not contact:
		return

	await send_notification(
		notification_type="security_freeze",
		to=contact.email,
		variables={
			"account_number": account.account_number,
			"rule": rules,
			"details": "Операция отклонена автоматической системой безопасности.",
		},
	)
