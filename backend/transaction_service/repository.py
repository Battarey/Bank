"""Репозиторий для выполнения банковских операций и работы с историей транзакций."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.database_core.base_repository import BaseRepository

from .exceptions import AccountNotFound


class TransactionRepository(BaseRepository[models.Transaction]):
	"""Инкапсулирует работу с транзакциями и блокировками счетов."""

	def __init__(self, session: AsyncSession):
		super().__init__(session, models.Transaction)

	async def get_by_idempotency_key(self, key: UUID) -> models.Transaction | None:
		"""Возвращает транзакцию по ключу идемпотентности."""
		stmt = select(models.Transaction).where(models.Transaction.idempotency_key == key)
		result = await self.session.execute(stmt)
		return result.scalar_one_or_none()

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

	async def get_owner_contact(self, user_id: UUID) -> models.Contact | None:
		"""Возвращает контактные данные владельца (для уведомлений)."""
		return await self.session.get(models.Contact, user_id)
