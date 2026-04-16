"""Репозиторий для выполнения проверок безопасности и доступа к данным транзакций."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
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

	async def get_total_amount_since(self, account_id: UUID, since: datetime, direction: str | None = None) -> Decimal:
		"""Возвращает сумму успешных транзакций по счёту за указанный период."""
		stmt = select(func.coalesce(func.sum(models.Transaction.amount), Decimal("0"))).where(
			models.Transaction.account_id == account_id,
			models.Transaction.created_at >= since,
			models.Transaction.status == "completed",
		)
		if direction:
			stmt = stmt.where(models.Transaction.direction == direction)
		result = await self.session.execute(stmt)
		return result.scalar()

	async def get_transaction_count_since(self, account_id: UUID, since: datetime, direction: str | None = None) -> int:
		"""Возвращает количество успешных транзакций по счёту за указанный период."""
		stmt = (
			select(func.count())
			.select_from(models.Transaction)
			.where(
				models.Transaction.account_id == account_id,
				models.Transaction.created_at >= since,
				models.Transaction.status == "completed",
			)
		)
		if direction:
			stmt = stmt.where(models.Transaction.direction == direction)
		result = await self.session.execute(stmt)
		return result.scalar() or 0

	async def get_pattern_count(
		self,
		account_id: UUID,
		since: datetime,
		lower_bound: Decimal,
		upper_bound: Decimal,
	) -> int:
		"""Возвращает количество транзакций в диапазоне сумм (паттерн дробления)."""
		stmt = (
			select(func.count())
			.select_from(models.Transaction)
			.where(
				models.Transaction.account_id == account_id,
				models.Transaction.created_at >= since,
				models.Transaction.amount >= lower_bound,
				models.Transaction.amount < upper_bound,
				models.Transaction.status == "completed",
			)
		)
		result = await self.session.execute(stmt)
		return result.scalar() or 0

	async def get_round_amount_count(
		self,
		account_id: UUID,
		since: datetime,
		floor: Decimal,
		step: Decimal,
	) -> int:
		"""Возвращает количество транзакций с крупными круглыми суммами."""
		stmt = (
			select(func.count())
			.select_from(models.Transaction)
			.where(
				models.Transaction.account_id == account_id,
				models.Transaction.created_at >= since,
				models.Transaction.amount >= floor,
				func.mod(models.Transaction.amount, step) == 0,
				models.Transaction.status == "completed",
			)
		)
		result = await self.session.execute(stmt)
		return result.scalar() or 0
