from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from shared.bootstrap import get_container
from shared.database_core.uow import SqlAlchemyUnitOfWork

from .repository import SecurityRepository

# Получаем инфраструктурный контейнер
container = get_container()
SessionLocal = container.session_factory


class SecurityUnitOfWork(SqlAlchemyUnitOfWork):
	"""Unit of Work для Security Service.

	Обеспечивает атомарный доступ к данным счетов и транзакций для AML-анализа.
	Поддерживает механизм Domain Events для будущих интеграций (например, автоблокировки).

	Attributes:
		accounts: Репозиторий для проверки счетов и истории операций.
	"""

	def __init__(self):
		"""Инициализирует UoW с фабрикой сессий по умолчанию."""
		super().__init__(SessionLocal)
		self.accounts: SecurityRepository | None = None

	async def __aenter__(self) -> SecurityUnitOfWork:
		"""Вход в контекстный менеджер и инициализация репозитория."""
		uow = await super().__aenter__()
		if self._session:
			self.accounts = SecurityRepository(self._session)
		return uow

	async def __aexit__(
		self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any | None
	) -> None:
		"""Выход из контекстного менеджера и очистка ресурсов."""
		await super().__aexit__(exc_type, exc_val, exc_tb)
		self.accounts = None


async def get_uow() -> AsyncGenerator[SecurityUnitOfWork, None]:
	"""Производит экземпляр Unit of Work для использования в FastAPI Depends.

	Yields:
		SecurityUnitOfWork: Контекстный менеджер для управления транзакцией.
	"""
	uow = SecurityUnitOfWork()
	yield uow
