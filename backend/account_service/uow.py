from __future__ import annotations
"""Unit of Work для Account Service."""

from typing import Any, Type, AsyncGenerator

from shared.database_core.uow import SqlAlchemyUnitOfWork
from shared.database_core.db import async_sessionmaker, engine
from sqlalchemy.ext.asyncio import AsyncSession
from .repository import AccountRepository
from .queries.repository import AccountQueryRepository

# Создаем локальный sessionmaker для сервиса
SessionLocal = async_sessionmaker(
	bind=engine,
	class_=AsyncSession,
	expire_on_commit=False,
)


class AccountUnitOfWork(SqlAlchemyUnitOfWork):
	"""UoW для Account Service, предоставляющий доступ к репозиторию счетов."""

	def __init__(self):
		super().__init__(SessionLocal)
		self.accounts: AccountRepository | None = None
		self.account_queries: AccountQueryRepository | None = None

	async def __aenter__(self) -> AccountUnitOfWork:
		uow = await super().__aenter__()
		if self._session:
			self.accounts = AccountRepository(self._session)
			self.account_queries = AccountQueryRepository(self._session)
		return uow

	async def __aexit__(self, exc_type: Type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any | None) -> None:
		await super().__aexit__(exc_type, exc_val, exc_tb)
		self.accounts = None
		self.account_queries = None


async def get_uow() -> AsyncGenerator[AccountUnitOfWork, None]:
	"""Зависимость для FastAPI, возвращающая Unit of Work."""
	uow = AccountUnitOfWork()
	yield uow
