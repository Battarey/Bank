"""Репозиторий для управления банковскими счетами и проверки их владельцев."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.database_core.base_repository import BaseRepository

from ..core.exceptions import AccountNotFound, AccountOwnerNotFound


class AccountRepository(BaseRepository[models.BankAccount]):
	"""Инкапсулирует работу с банковскими счетами."""

	def __init__(self, session: AsyncSession):
		super().__init__(session, models.BankAccount)

	async def get_active_owner(self, user_id: UUID) -> models.User:
		"""Проверяет существование и активность владельца счёта."""
		user = await self.session.get(models.User, user_id)
		if user is None or user.status != "active":
			raise AccountOwnerNotFound("Владелец не найден или не активен.")
		return user

	async def get_by_user(self, user_id: UUID, account_id: UUID) -> models.BankAccount:
		"""Возвращает счёт по ID, проверяя принадлежность пользователю."""
		account = await self.get(account_id)
		if account is None or account.client_id != user_id:
			raise AccountNotFound("Счёт не найден.")
		return account

	async def count_open_by_type(self, user_id: UUID, acc_type: str, currency: str) -> int:
		"""Считает количество открытых счетов конкретного типа и валюты."""
		stmt = select(models.BankAccount).where(
			models.BankAccount.client_id == user_id,
			models.BankAccount.type == acc_type,
			models.BankAccount.currency == currency,
			models.BankAccount.status == "open",
		)
		result = await self.session.execute(stmt)
		return len(result.scalars().all())

	async def get_owner_contact(self, user_id: UUID) -> models.Contact | None:
		"""Возвращает контактные данные владельца (для уведомлений)."""
		return await self.session.get(models.Contact, user_id)

	async def get_by_number(self, number: str) -> models.BankAccount | None:
		"""Возвращает счёт по его уникальному номеру."""
		stmt = select(models.BankAccount).where(models.BankAccount.account_number == number)
		result = await self.session.execute(stmt)
		return result.scalar_one_or_none()

	async def is_number_unique(self, number: str) -> bool:
		"""Проверяет уникальность номера счёта."""
		stmt = select(models.BankAccount.id).where(models.BankAccount.account_number == number)
		result = await self.session.execute(stmt)
		return result.first() is None

	async def get_open_accounts(self, user_id: UUID) -> list[models.BankAccount]:
		"""Возвращает все открытые счета пользователя."""
		stmt = select(models.BankAccount).where(
			models.BankAccount.client_id == user_id,
			models.BankAccount.status == "open",
		)
		result = await self.session.execute(stmt)
		return list(result.scalars().all())

	async def get_system_frozen_accounts(self, user_id: UUID) -> list[models.BankAccount]:
		"""Возвращает счета пользователя, замороженные системой."""
		stmt = select(models.BankAccount).where(
			models.BankAccount.client_id == user_id,
			models.BankAccount.status == "frozen",
			models.BankAccount.frozen_by == "system",
		)
		result = await self.session.execute(stmt)
		return list(result.scalars().all())
