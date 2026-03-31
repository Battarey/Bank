"""Репозиторий для выполнения банковских операций и работы с историей транзакций."""

from typing import Sequence
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.database_core.base_repository import BaseRepository
from .exceptions import AccountNotFound


class TransactionRepository(BaseRepository[models.Transaction]):
	"""Инкапсулирует работу с транзакциями и блокировками счетов."""

	def __init__(self, session: AsyncSession):
		super().__init__(session, models.Transaction)

	async def lock_accounts(self, account_ids: list[UUID]) -> dict[UUID, models.BankAccount]:
		"""Атомарно блокирует несколько счетов в БД (FOR UPDATE).
		
		Сортировка ID важна для исключения взаимных блокировок (Deadlocks).
		"""
		stmt = (
			select(models.BankAccount)
			.where(models.BankAccount.id.in_(sorted(account_ids)))
			.with_for_update()
			.order_by(models.BankAccount.id)
		)
		result = await self.session.execute(stmt)
		accounts = {acc.id: acc for acc in result.scalars().all()}
		return accounts

	async def get_account_for_update(self, account_id: UUID) -> models.BankAccount:
		"""Возвращает счёт с блокировкой на уровне БД (FOR UPDATE)."""
		stmt = (
			select(models.BankAccount)
			.where(models.BankAccount.id == account_id)
			.with_for_update()
		)
		result = await self.session.execute(stmt)
		account = result.scalar_one_or_none()
		if not account:
			raise AccountNotFound(f"Счёт {account_id} не найден.")
		return account

	async def get_account(self, account_id: UUID) -> models.BankAccount:
		"""Возвращает счёт без блокировки."""
		account = await self.session.get(models.BankAccount, account_id)
		if not account:
			raise AccountNotFound(f"Счёт {account_id} не найден.")
		return account

	async def list_by_account(self, account_id: UUID, limit: int = 50, offset: int = 0) -> Sequence[models.Transaction]:
		"""Возвращает историю операций по конкретному счёту."""
		stmt = (
			select(models.Transaction)
			.where(
				or_(
					models.Transaction.account_id == account_id,
					models.Transaction.related_account_id == account_id
				)
			)
			.order_by(models.Transaction.created_at.desc())
			.limit(limit)
			.offset(offset)
		)
		result = await self.session.execute(stmt)
		return result.scalars().all()

	async def get_owner_contact(self, user_id: UUID) -> models.Contact | None:
		"""Возвращает контактные данные владельца (для уведомлений)."""
		return await self.session.get(models.Contact, user_id)

	async def list_with_total(
		self,
		account_id: UUID,
		limit: int = 20,
		offset: int = 0,
		tx_type: str | None = None,
		direction: str | None = None,
	) -> tuple[Sequence[models.Transaction], int]:
		"""Возвращает историю операций по счету и их общее количество (для пагинации)."""
		from sqlalchemy import func

		filters = [models.Transaction.account_id == account_id]
		if tx_type:
			filters.append(models.Transaction.type == tx_type)
		if direction:
			filters.append(models.Transaction.direction == direction)

		# Подсчет total
		count_stmt = select(func.count()).select_from(models.Transaction).where(*filters)
		total = (await self.session.execute(count_stmt)).scalar_one()

		# Получение данных
		stmt = (
			select(models.Transaction)
			.where(*filters)
			.order_by(models.Transaction.created_at.desc())
			.limit(min(limit, 100))
			.offset(offset)
		)
		result = await self.session.execute(stmt)
		transactions = result.scalars().all()

		return transactions, total
