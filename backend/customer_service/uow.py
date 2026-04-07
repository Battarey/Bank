from __future__ import annotations
"""Unit of Work для Customer Service."""

from typing import Any, Type, AsyncGenerator

from shared.database_core.uow import SqlAlchemyUnitOfWork
from shared.bootstrap import get_container
from .repository import CustomerRepository
from .queries.repository import CustomerQueryRepository

class CustomerUnitOfWork(SqlAlchemyUnitOfWork):
	"""UoW для Customer Service, предоставляющий доступ к репозиторию клиентов."""

	def __init__(self):
		"""Инициализирует UoW с фабрикой сессий из контейнера."""
		container = get_container()
		session_factory = container.session_factory
		super().__init__(session_factory)
		self.customers: CustomerRepository | None = None
		self.customer_queries: CustomerQueryRepository | None = None

	async def __aenter__(self) -> CustomerUnitOfWork:
		uow = await super().__aenter__()
		if self._session:
			self.customers = CustomerRepository(self._session)
			self.customer_queries = CustomerQueryRepository(self._session)
		return uow

	async def __aexit__(self, exc_type: Type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any | None) -> None:
		await super().__aexit__(exc_type, exc_val, exc_tb)
		self.customers = None
		self.customer_queries = None


async def get_uow() -> AsyncGenerator[CustomerUnitOfWork, None]:
	"""Зависимость для FastAPI, возвращающая Unit of Work."""
	uow = CustomerUnitOfWork()
	yield uow
