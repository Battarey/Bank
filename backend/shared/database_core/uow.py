"""Абстракция Unit of Work (UoW) для управления атомарностью операций."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
	from sqlalchemy.ext.asyncio import AsyncSession

	from .db import async_sessionmaker


class AbstractUnitOfWork(abc.ABC):
	"""Абстрактный базовый класс для Unit of Work."""

	def __init__(self):
		self._events: list = []

	async def __aenter__(self) -> AbstractUnitOfWork:
		return self

	async def __aexit__(
		self,
		exc_type: type[BaseException] | None,
		exc_val: BaseException | None,
		exc_tb: Any | None,
	) -> None:
		if exc_type:
			await self.rollback()

	@abc.abstractmethod
	async def commit(self) -> None:
		"""Фиксирует изменения в текущей транзакции."""

	@abc.abstractmethod
	async def rollback(self) -> None:
		"""Откатывает изменения в текущей транзакции."""

	def add_event(self, event) -> None:
		"""Добавляет событие в очередь Unit of Work."""
		self._events.append(event)

	def collect_events(self) -> list:
		"""Возвращает накопленные события и очищает очередь."""
		events = self._events
		self._events = []
		return events

	async def publish_events(self) -> None:
		"""Публикует накопленные события через MessageBus."""
		from shared.rabbitmq.bus import MessageBus

		events = self.collect_events()
		if events:
			await MessageBus.handle(events)


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
	"""Реализация Unit of Work на базе SQLAlchemy."""

	@property
	def session(self) -> AsyncSession:
		"""Возвращает текущую сессию SQLAlchemy."""
		if self._session is None:
			raise RuntimeError("Сессия не инициализирована. Используйте Unit of Work внутри контекстного менеджера 'async with'.")
		return self._session

	def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
		super().__init__()
		self.session_factory = session_factory
		self._session: AsyncSession | None = None

	async def __aenter__(self) -> SqlAlchemyUnitOfWork:
		self._session = self.session_factory()
		return await super().__aenter__()

	async def __aexit__(
		self,
		exc_type: type[BaseException] | None,
		exc_val: BaseException | None,
		exc_tb: Any | None,
	) -> None:
		await super().__aexit__(exc_type, exc_val, exc_tb)
		if self._session:
			await self._session.close()
			self._session = None

	async def commit(self) -> None:
		if self._session:
			await self._session.commit()
			await self.publish_events()

	async def rollback(self) -> None:
		if self._session:
			await self._session.rollback()
