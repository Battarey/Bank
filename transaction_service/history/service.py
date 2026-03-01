"""Бизнес-логика просмотра истории транзакций."""

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from transaction_service.exceptions import AccountNotFound

logger = logging.getLogger("transaction_service")


async def list_transactions(
	session: AsyncSession,
	user_id: UUID,
	account_id: UUID,
	*,
	limit: int = 20,
	offset: int = 0,
	tx_type: str | None = None,
	direction: str | None = None,
) -> tuple[list[models.Transaction], int]:
	"""Возвращает транзакции по счёту с пагинацией и фильтрами.

	Args:
		session: Сессия SQLAlchemy.
		user_id: UUID пользователя (для проверки принадлежности).
		account_id: UUID счёта.
		limit: Кол-во записей на страницу (макс 100).
		offset: Смещение.
		tx_type: Фильтр по типу (deposit / withdrawal / transfer).
		direction: Фильтр по направлению (incoming / outgoing).

	Returns:
		(list[Transaction], total_count)
	"""

	# 1. Проверяем принадлежность счёта
	account = await session.get(models.BankAccount, account_id)
	if account is None or account.client_id != user_id:
		raise AccountNotFound("Счёт не найден.")

	# 2. Базовый фильтр
	base_filter = [models.Transaction.account_id == account_id]

	if tx_type is not None:
		base_filter.append(models.Transaction.type == tx_type)

	if direction is not None:
		base_filter.append(models.Transaction.direction == direction)

	# 3. Считаем общее количество
	count_stmt = select(func.count()).select_from(models.Transaction).where(*base_filter)
	total = (await session.execute(count_stmt)).scalar_one()

	# 4. Выбираем записи
	stmt = (
		select(models.Transaction)
		.where(*base_filter)
		.order_by(models.Transaction.created_at.desc())
		.limit(min(limit, 100))
		.offset(offset)
	)
	result = await session.execute(stmt)
	transactions = list(result.scalars().all())

	return transactions, total
