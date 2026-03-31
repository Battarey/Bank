from __future__ import annotations
"""Unit of Work для Customer Service."""

from typing import Any, Type, AsyncGenerator

from shared.database_core.uow import SqlAlchemyUnitOfWork
from shared.database_core.db import async_sessionmaker, engine
from sqlalchemy.ext.asyncio import AsyncSession
from .repository import CustomerRepository

# Создаем локальный sessionmaker для сервиса
SessionLocal = async_sessionmaker(
	bind=engine,
	class_=AsyncSession,
	expire_on_commit=False,
)


class CustomerUnitOfWork(SqlAlchemyUnitOfWork):
	"""UoW для Customer Service, предоставляющий доступ к репозиторию клиентов."""

	def __init__(self):
		super().__init__(SessionLocal)
		self.customers: CustomerRepository | None = None

	async def __aenter__(self) -> CustomerUnitOfWork:
		uow = await super().__aenter__()
		if self._session:
			self.customers = CustomerRepository(self._session)
		return uow

	async def __aexit__(self, exc_type: Type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any | None) -> None:
		await super().__aexit__(exc_type, exc_val, exc_tb)
		self.customers = None


async def get_uow() -> AsyncGenerator[CustomerUnitOfWork, None]:
	"""Зависимость для FastAPI, возвращающая Unit of Work."""
	uow = CustomerUnitOfWork()
	yield uow
