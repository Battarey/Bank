from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from shared.bootstrap import get_container
from shared.database_core.uow import SqlAlchemyUnitOfWork

from ..repositories.auth import AuthRepository


class AuthUnitOfWork(SqlAlchemyUnitOfWork):
	"""Unit of Work для Auth Service.

	Обеспечивает атомарность операций аутентификации, смены ПИН-кода
	и разблокировки аккаунта с поддержкой публикации событий.

	Attributes:
		users: Репозиторий для работы с пользователями и их статусами.
	"""

	def __init__(self):
		"""Инициализирует UoW с фабрикой сессий из контейнера."""
		container = get_container()
		session_factory = container.session_factory
		super().__init__(session_factory)
		self.users: AuthRepository | None = None

	async def __aenter__(self) -> AuthUnitOfWork:
		"""Вход в контекстный менеджер и инициализация репозитория."""
		uow = await super().__aenter__()
		if self._session:
			self.users = AuthRepository(self._session)
		return uow

	async def __aexit__(
		self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any | None
	) -> None:
		"""Выход из контекстного менеджера и очистка ресурсов."""
		await super().__aexit__(exc_type, exc_val, exc_tb)
		self.users = None


async def get_uow() -> AsyncGenerator[AuthUnitOfWork, None]:
	"""Производит экземпляр Unit of Work для использования в FastAPI Depends.

	Yields:
		AuthUnitOfWork: Контекстный менеджер для управления транзакцией.
	"""
	uow = AuthUnitOfWork()
	yield uow
