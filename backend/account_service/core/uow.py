from __future__ import annotations

"""Unit of Work для Account Service."""

from collections.abc import AsyncGenerator
from typing import Any

from shared.bootstrap import get_container
from shared.database_core.uow import SqlAlchemyUnitOfWork

from ..repositories.account import AccountRepository
from ..repositories.queries import AccountQueryRepository


class AccountUnitOfWork(SqlAlchemyUnitOfWork):
	"""UoW для Account Service, предоставляющий доступ к репозиторию счетов."""

	def __init__(self):
		container = get_container()
		session_factory = container.session_factory
		super().__init__(session_factory)
		self.accounts: AccountRepository | None = None
		self.account_queries: AccountQueryRepository | None = None

	async def __aenter__(self) -> AccountUnitOfWork:
		uow = await super().__aenter__()
		if self._session:
			self.accounts = AccountRepository(self._session)
			self.account_queries = AccountQueryRepository(self._session)
		return uow

	async def __aexit__(
		self,
		exc_type: type[BaseException] | None,
		exc_val: BaseException | None,
		exc_tb: Any | None,
	) -> None:
		await super().__aexit__(exc_type, exc_val, exc_tb)
		self.accounts = None
		self.account_queries = None


async def get_uow() -> AsyncGenerator[AccountUnitOfWork, None]:
	"""Зависимость для FastAPI, возвращающая Unit of Work."""
	uow = AccountUnitOfWork()
	yield uow
