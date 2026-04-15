"""Репозиторий для валютных операций и управления банковскими счетами."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.database_core.base_repository import BaseRepository

from ..core.exceptions import AccountNotFound


class CurrencyRepository(BaseRepository[models.BankAccount]):
	"""Инкапсулирует работу с банковскими счетами и транзакциями в валютном сервисе."""

	def __init__(self, session: AsyncSession):
		super().__init__(session, models.BankAccount)

	async def lock_accounts(self, account_ids: list[UUID]) -> dict[UUID, models.BankAccount]:
		"""Атомарно блокирует несколько счетов в БД (FOR UPDATE).

		Сортировка ID важна для исключения Deadlocks.
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

	async def get_by_user(self, user_id: UUID, account_id: UUID) -> models.BankAccount:
		"""Возвращает счёт по ID, проверяя принадлежность пользователю."""
		account = await self.session.get(models.BankAccount, account_id)
		if account is None or account.client_id != user_id:
			raise AccountNotFound(f"Счёт {account_id} не найден.")
		return account

	async def get_owner_contact(self, user_id: UUID) -> models.Contact | None:
		"""Возвращает контактные данные владельца (для уведомлений)."""
		return await self.session.get(models.Contact, user_id)
