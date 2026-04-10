"""Репозиторий для работы с данными клиентов (профили, документы, контакты)."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.database_core.base_repository import BaseRepository

from .exceptions import UpdateDataConflict, UpdateDataNotFound


class CustomerRepository(BaseRepository[models.User]):
	"""Инкапсулирует работу с агрегатом Пользователь + Профили."""

	def __init__(self, session: AsyncSession):
		super().__init__(session, models.User)

	# ── Работа с профилями ────────────────────────────────────────────────

	async def get_personal_data(self, client_id: UUID) -> models.PersonalData | None:
		"""Возвращает персональные данные клиента."""
		return await self.session.get(models.PersonalData, client_id)

	async def get_passport(self, client_id: UUID) -> models.Passport | None:
		"""Возвращает паспортные данные клиента."""
		return await self.session.get(models.Passport, client_id)

	async def get_contact(self, client_id: UUID) -> models.Contact | None:
		"""Возвращает контактные данные клиента."""
		return await self.session.get(models.Contact, client_id)

	async def get_identifier(self, client_id: UUID) -> models.Identifier | None:
		"""Возвращает ИНН/СНИЛС клиента."""
		return await self.session.get(models.Identifier, client_id)

	# ── Проверки уникальности (Blind Index) ───────────────────────────────

	async def check_passport_unique(self, passport_hash: str, exclude_client_id: UUID | None = None) -> None:
		"""Проверяет, не занят ли паспорт другим клиентом."""
		stmt = select(models.Passport).where(models.Passport.passport_hash == passport_hash)
		if exclude_client_id:
			stmt = stmt.where(models.Passport.client_id != exclude_client_id)
		
		result = await self.session.execute(stmt)
		if result.scalar_one_or_none():
			raise UpdateDataConflict("Паспорт с такой серией/номером уже зарегистрирован.")

	async def check_contacts_unique(
		self, 
		email_hash: str | None = None, 
		phone_hash: str | None = None,
		exclude_client_id: UUID | None = None
	) -> None:
		"""Проверяет уникальность email и телефона."""
		conditions = []
		if email_hash:
			conditions.append(models.Contact.email_hash == email_hash)
		if phone_hash:
			conditions.append(models.Contact.phone_hash == phone_hash)
		
		if not conditions:
			return

		stmt = select(models.Contact).where(or_(*conditions))
		if exclude_client_id:
			stmt = stmt.where(models.Contact.client_id != exclude_client_id)
		
		result = await self.session.execute(stmt)
		if result.scalar_one_or_none():
			raise UpdateDataConflict("Email или номер телефона уже используется другим клиентом.")

	async def check_identifiers_unique(
		self, 
		inn_hash: str | None = None, 
		snils_hash: str | None = None,
		exclude_client_id: UUID | None = None
	) -> None:
		"""Проверяет уникальность ИНН и СНИЛС."""
		conditions = []
		if inn_hash:
			conditions.append(models.Identifier.inn_hash == inn_hash)
		if snils_hash:
			conditions.append(models.Identifier.snils_hash == snils_hash)
		
		if not conditions:
			return

		stmt = select(models.Identifier).where(or_(*conditions))
		if exclude_client_id:
			stmt = stmt.where(models.Identifier.client_id != exclude_client_id)
		
		result = await self.session.execute(stmt)
		if result.scalar_one_or_none():
			raise UpdateDataConflict("ИНН или СНИЛС уже зарегистрирован в системе.")

	# ── Вспомогательные методы ────────────────────────────────────────────

	async def add_profile_part(self, entity: Any) -> None:
		"""Добавляет часть профиля (Passport, Contact и т.д.) в сессию."""
		self.session.add(entity)

	async def get_active_user(self, user_id: UUID) -> models.User:
		"""Возвращает пользователя, если он существует (используется для проверок)."""
		user = await self.get(user_id)
		if not user:
			raise UpdateDataNotFound(f"Пользователь {user_id} не найден.")
		return user

	async def get_open_accounts(self, client_id: UUID) -> Sequence[models.BankAccount]:
		"""Возвращает все активные (незамороженные и неоткрытые) счета клиента."""
		stmt = select(models.BankAccount).where(
			models.BankAccount.client_id == client_id,
			models.BankAccount.status == "open",
		).with_for_update()
		result = await self.session.execute(stmt)
		return result.scalars().all()
