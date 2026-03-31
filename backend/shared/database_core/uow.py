"""Абстракция Unit of Work (UoW) для управления атомарностью операций."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
	from sqlalchemy.ext.asyncio import AsyncSession
	from .db import async_sessionmaker


class AbstractUnitOfWork(abc.ABC):
	"""Абстрактный базовый класс для Unit of Work."""

	async def __aenter__(self) -> AbstractUnitOfWork:
		return self

	async def __aexit__(self, exc_type: Type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any | None) -> None:
		await self.rollback()

	@abc.abstractmethod
	async def commit(self) -> None:
		"""Фиксирует изменения в текущей транзакции."""

	@abc.abstractmethod
	async def rollback(self) -> None:
		"""Откатывает изменения в текущей транзакции."""


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
	"""Реализация Unit of Work на базе SQLAlchemy."""

	def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
		self.session_factory = session_factory
		self._session: AsyncSession | None = None

	async def __aenter__(self) -> SqlAlchemyUnitOfWork:
		self._session = self.session_factory()
		return await super().__aenter__()

	async def __aexit__(self, exc_type: Type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any | None) -> None:
		await super().__aexit__(exc_type, exc_val, exc_tb)
		if self._session:
			await self._session.close()
			self._session = None

	async def commit(self) -> None:
		if self._session:
			await self._session.commit()

	async def rollback(self) -> None:
		if self._session:
			await self._session.rollback()
