"""Базовый класс репозитория для работы с SQLAlchemy."""

from typing import Generic, Sequence, TypeVar, Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
	"""Базовая реализация паттерна Repository.

	Инкапсулирует общие операции с базой данных (GET, LIST, ADD, DELETE).
	"""

	def __init__(self, session: AsyncSession, model: type[ModelT]):
		self.session = session
		self.model = model

	async def get(self, id: UUID) -> ModelT | None:
		"""Возвращает запись по её первичному ключу (UUID)."""
		return await self.session.get(self.model, id)

	async def list(self, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
		"""Возвращает список записей с поддержкой пагинации."""
		stmt = select(self.model).limit(limit).offset(offset)
		result = await self.session.execute(stmt)
		return result.scalars().all()

	async def add(self, entity: ModelT) -> ModelT:
		"""Добавляет сущность в сессию для последующего коммита."""
		self.session.add(entity)
		return entity

	async def delete(self, id: UUID) -> bool:
		"""Удаляет запись по её идентификатору."""
		stmt = delete(self.model).where(self.model.id == id)
		result = await self.session.execute(stmt)
		return result.rowcount > 0

	async def commit(self) -> None:
		"""Фиксирует изменения в текущей сессии."""
		await self.session.commit()

	async def rollback(self) -> None:
		"""Откатывает изменения в текущей сессии."""
		await self.session.rollback()

	async def refresh(self, entity: ModelT) -> None:
		"""Обновляет состояние сущности из базы данных."""
		await self.session.refresh(entity)
