"""Базовый класс для Read-репозиториев (CQRS Query Layer)."""

from typing import Any, Sequence, TypeVar, Type
from sqlalchemy import text, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel


SchemaT = TypeVar("SchemaT", bound=BaseModel)


class BaseQueryRepository:
	"""Инкапсулирует выполнение высокопроизводительных сырых SQL-запросов.
	
	Используется для CQRS Query Model (чтение данных без оверхеда ORM).
	"""

	def __init__(self, session: AsyncSession):
		self.session = session

	async def _fetch_rows(self, query: str, params: dict[str, Any] | None = None) -> Sequence[RowMapping]:
		"""Выполняет сырой SQL и возвращает список RowMapping (dict-like)."""
		result = await self.session.execute(text(query), params or {})
		return result.mappings().all()

	async def _fetch_one(self, query: str, params: dict[str, Any] | None = None) -> RowMapping | None:
		"""Выполняет сырой SQL и возвращает одну строку как RowMapping или None."""
		result = await self.session.execute(text(query), params or {})
		return result.mappings().first()

	async def _get_total(self, query: str, params: dict[str, Any] | None = None) -> int:
		"""Выполняет запрос для подсчета количества записей (scalar)."""
		result = await self.session.execute(text(query), params or {})
		return result.scalar_one()

	def _map_to_schema(self, row: RowMapping, schema: Type[SchemaT]) -> SchemaT:
		"""Мапит RowMapping в Pydantic-схему."""
		return schema.model_validate(row, from_attributes=True)

	def _map_to_schemas(self, rows: Sequence[RowMapping], schema: Type[SchemaT]) -> list[SchemaT]:
		"""Мапит список RowMapping в список Pydantic-схем."""
		return [self._map_to_schema(row, schema) for row in rows]
