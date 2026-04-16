"""Репозиторий для выполнения проверок безопасности и доступа к данным транзакций."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import models
from shared.database_core.base_repository import BaseRepository

from ..core.exceptions import AccountNotFound


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
