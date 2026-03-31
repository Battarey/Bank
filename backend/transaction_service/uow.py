from __future__ import annotations
from typing import Any, Type, AsyncGenerator

from shared.database_core.uow import SqlAlchemyUnitOfWork
from shared.database_core.db import SessionLocal
from .repository import TransactionRepository
from .history.repository import TransactionQueryRepository


class TransactionUnitOfWork(SqlAlchemyUnitOfWork):
	"""UoW для Transaction Service, предоставляющий доступ к репозиторию транзакций."""

	def __init__(self):
		super().__init__(SessionLocal)
		self.transactions: TransactionRepository | None = None
		self.history_query: TransactionQueryRepository | None = None

	async def __aenter__(self) -> TransactionUnitOfWork:
		uow = await super().__aenter__()
		if self._session:
			self.transactions = TransactionRepository(self._session)
			self.history_query = TransactionQueryRepository(self._session)
		return uow

	async def __aexit__(self, exc_type: Type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any | None) -> None:
		await super().__aexit__(exc_type, exc_val, exc_tb)
		self.transactions = None
		self.history_query = None


async def get_uow() -> AsyncGenerator[TransactionUnitOfWork, None]:
	"""Зависимость для FastAPI, возвращающая Unit of Work."""
	uow = TransactionUnitOfWork()
	yield uow
