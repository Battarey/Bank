from __future__ import annotations
from typing import Any, Type, AsyncGenerator

from shared.database_core.uow import SqlAlchemyUnitOfWork
from shared.bootstrap import get_container
from .repository import AuthRepository

# Получаем фабрику сессий из контейнера
container = get_container()
SessionLocal = container.session_factory


class AuthUnitOfWork(SqlAlchemyUnitOfWork):
	"""Unit of Work для Auth Service.

	Обеспечивает атомарность операций аутентификации, смены ПИН-кода 
	и разблокировки аккаунта с поддержкой публикации событий.

	Attributes:
		users: Репозиторий для работы с пользователями и их статусами.
	"""

	def __init__(self):
		"""Инициализирует UoW с фабрикой сессий по умолчанию."""
		super().__init__(SessionLocal)
		self.users: AuthRepository | None = None

	async def __aenter__(self) -> AuthUnitOfWork:
		"""Вход в контекстный менеджер и инициализация репозитория."""
		uow = await super().__aenter__()
		if self._session:
			self.users = AuthRepository(self._session)
		return uow

	async def __aexit__(
		self, 
		exc_type: Type[BaseException] | None, 
		exc_val: BaseException | None, 
		exc_tb: Any | None
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
