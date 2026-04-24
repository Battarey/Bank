"""Async-подключение к PostgreSQL History (engine, session factory)."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.bootstrap import get_container

# ВНИМАНИЕ: Эти функции требуют предварительного вызова bootstrap() в main.py
class InfrastructureProxy:
	"""Прокси для отложенного доступа к ресурсам BootstrapContainer.

	Позволяет импортировать engine/SessionLocal на уровне модуля без вызова bootstrap(),
	что критично для сбора тестов в pytest.
	"""

	def __init__(self, attr_name: str):
		self._attr_name = attr_name

	@property
	def _obj(self):
		return getattr(get_container(), self._attr_name)

	def __getattr__(self, name: str):
		return getattr(self._obj, name)

	def __call__(self, *args, **kwargs):
		return self._obj(*args, **kwargs)


# Прокси-объекты для обратной совместимости и удобства
history_engine = InfrastructureProxy("history_engine")
HistorySessionLocal = InfrastructureProxy("history_session_factory")


async def get_history_session() -> AsyncGenerator[AsyncSession, None]:
	"""Асинхронная зависимость FastAPI, возвращающая сессию к postgres_history."""
	async with HistorySessionLocal() as session:
		yield session


async def ping_db() -> bool:
	"""Проверить доступность базы данных истории."""
	async with history_engine.connect() as conn:
		await conn.execute(text("SELECT 1"))
		return True


__all__ = [
	"AsyncSession",
	"HistorySessionLocal",
	"get_history_session",
	"history_engine",
	"ping_db",
]
