from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from shared.bootstrap import get_container
from shared.database_core.uow import SqlAlchemyUnitOfWork

from .repository import CurrencyRepository


class CurrencyUnitOfWork(SqlAlchemyUnitOfWork):
	"""Unit of Work для Currency Service.

	Управляет атомарностью операций со счетами и транзакциями,
	обеспечивая консистентность данных при обмене валют.

	Attributes:
		accounts: Репозиторий для работы с банковскими счетами.
	"""

	def __init__(self):
		"""Инициализирует UoW с фабрикой сессий из контейнера."""
		container = get_container()
		session_factory = container.session_factory
		super().__init__(session_factory)
		self.accounts: CurrencyRepository | None = None

	async def __aenter__(self) -> CurrencyUnitOfWork:
		"""Вход в контекстный менеджер и инициализация репозиториев."""
		uow = await super().__aenter__()
		if self._session:
			self.accounts = CurrencyRepository(self._session)
		return uow

	async def __aexit__(
		self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any | None
	) -> None:
		"""Выход из контекстного менеджера и очистка репозиториев."""
		await super().__aexit__(exc_type, exc_val, exc_tb)
		self.accounts = None


async def get_uow() -> AsyncGenerator[CurrencyUnitOfWork, None]:
	"""Производит экземпляр Unit of Work для использования в FastAPI Depends.

	Yields:
		CurrencyUnitOfWork: Контекстный менеджер для управления транзакцией.
	"""
	uow = CurrencyUnitOfWork()
	yield uow
