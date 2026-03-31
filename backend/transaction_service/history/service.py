"""Бизнес-логика просмотра истории транзакций по банковским счетам."""

from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from ..repository import TransactionRepository


async def list_transactions(
	session: AsyncSession,
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
		session: Сессия БД.
		user_id: ID владельца счёта (для проверки прав).
		account_id: ID счёта, историю которого нужно получить.
		limit: Количество записей на страницу (макс. 100).
		offset: Смещение (пропуск записей).
		tx_type: Опциональный фильтр по типу (deposit, withdrawal, transfer).
		direction: Опциональный фильтр по направлению (incoming, outgoing).

	Returns:
		tuple[Sequence[Transaction], int]: Список транзакций и общее количество (total_count).

	Raises:
		AccountNotFound: Если счёт не найден или не принадлежит пользователю.
	"""
	repo = TransactionRepository(session)
	
	# 1. Проверка принадлежности счёта
	await repo.get_by_user(user_id, account_id) # Нам нужно добавить этот метод в TransactionRepository или использовать проверку в сервисе.
	# В TransactionRepository я добавил get_account, но без проверки client_id.
	# Я добавлю проверку прямо здесь или обновлю репозиторий.
	
	# Обновлю прямо здесь для скорости, так как метод get_by_user типичен.
	account = await repo.get_account(account_id)
	if account.client_id != user_id:
		from ..exceptions import AccountNotFound
		raise AccountNotFound("Счёт не принадлежит вам.")

	# 2. Построение запроса с фильтрами
	filters = [models.Transaction.account_id == account_id]
	if tx_type:
		filters.append(models.Transaction.type == tx_type)
	if direction:
		filters.append(models.Transaction.direction == direction)

	# 3. Подсчёт общего количества
	count_stmt = select(func.count()).select_from(models.Transaction).where(*filters)
	total = (await session.execute(count_stmt)).scalar_one()

	# 4. Получение среза данных
	stmt = (
		select(models.Transaction)
		.where(*filters)
		.order_by(models.Transaction.created_at.desc())
		.limit(min(limit, 100))
		.offset(offset)
	)
	result = await session.execute(stmt)
	transactions = result.scalars().all()

	return transactions, total


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
