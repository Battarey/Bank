"""Репозиторий для проверки учётных данных и управления статусом аккаунта."""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.database_core.base_repository import BaseRepository
from .exceptions import AuthNotFound


class AuthRepository(BaseRepository[models.User]):
	"""Инкапсулирует запросы для аутентификации и смены статусов."""

	def __init__(self, session: AsyncSession):
		super().__init__(session, models.User)

	async def get_by_phone(self, phone_hash: str) -> tuple[models.User, models.Contact] | None:
		"""Ищет пользователя по хешу номера телефона."""
		stmt = (
			select(models.User, models.Contact)
			.join(models.Contact, models.User.id == models.Contact.client_id)
			.where(models.Contact.phone_hash == phone_hash)
		)
		result = await self.session.execute(stmt)
		row = result.first()
		return row.tuple() if row else None

	async def get_by_email(self, email_hash: str) -> tuple[models.User, models.Contact] | None:
		"""Ищет пользователя по хешу email."""
		stmt = (
			select(models.User, models.Contact)
			.join(models.Contact, models.User.id == models.Contact.client_id)
			.where(models.Contact.email_hash == email_hash)
		)
		result = await self.session.execute(stmt)
		row = result.first()
		return row.tuple() if row else None

	async def get_user_with_contact(self, user_id: UUID) -> tuple[models.User, models.Contact]:
		"""Возвращает пользователя и его контакты по ID."""
		stmt = (
			select(models.User, models.Contact)
			.join(models.Contact, models.User.id == models.Contact.client_id)
			.where(models.User.id == user_id)
		)
		result = await self.session.execute(stmt)
		row = result.first()
		if not row:
			raise AuthNotFound(f"Пользователь {user_id} не найден.")
		return row.tuple()

	async def get_system_frozen_accounts(self, client_id: UUID) -> Sequence[models.BankAccount]:
		"""Возвращает счета, замороженные системой (при блокировке аккаунта)."""
		stmt = (
			select(models.BankAccount)
			.where(
				models.BankAccount.client_id == client_id,
				models.BankAccount.status == "frozen",
				models.BankAccount.frozen_by == "system",
			)
			.with_for_update()
		)
		result = await self.session.execute(stmt)
		return result.scalars().all()

	async def get_open_accounts(self, client_id: UUID) -> Sequence[models.BankAccount]:
		"""Возвращает все активные (незамороженные) счета клиента."""
		stmt = (
			select(models.BankAccount)
			.where(
				models.BankAccount.client_id == client_id,
				models.BankAccount.status == "open",
			)
			.with_for_update()
		)
		result = await self.session.execute(stmt)
		return result.scalars().all()
