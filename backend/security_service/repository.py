"""Репозиторий для выполнения проверок безопасности и доступа к данным транзакций."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.database_core.base_repository import BaseRepository

from .exceptions import AccountNotFound


class SecurityRepository(BaseRepository[models.BankAccount]):
	"""Инкапсулирует работу с банковскими счетами и транзакциями для AML-анализа."""

	def __init__(self, session: AsyncSession):
		super().__init__(session, models.BankAccount)

	async def get_account(self, account_id: UUID) -> models.BankAccount:
		"""Возвращает счёт по ID или выбрасывает исключение, если он не найден."""
		account = await self.session.get(models.BankAccount, account_id)
		if not account:
			raise AccountNotFound(f"Счёт {account_id} не найден.")
		return account

	async def get_all_by_account(self, account_id: UUID, filters: list = None) -> list[models.Transaction]:
		"""Возвращает список транзакций по счёту с применением фильтров."""
		stmt = select(models.Transaction).where(models.Transaction.account_id == account_id)
		if filters:
			stmt = stmt.where(*filters)
		result = await self.session.execute(stmt)
		return result.scalars().all()
