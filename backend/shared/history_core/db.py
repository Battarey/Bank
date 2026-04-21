"""Async-подключение к PostgreSQL History (engine, session factory)."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.bootstrap import get_container

# ВНИМАНИЕ: Эти функции требуют предварительного вызова bootstrap() в main.py
def _get_history_engine():
	return get_container().history_engine

def _get_history_session_factory():
	return get_container().history_session_factory


async def ping_db() -> bool:
	"""Проверить доступность базы данных истории."""
	engine = _get_history_engine()
	async with engine.connect() as conn:
		await conn.execute(text("SELECT 1"))
		return True


async def get_history_session() -> AsyncGenerator[AsyncSession, None]:
	"""Асинхронная зависимость FastAPI, возвращающая сессию к postgres_history."""
	session_factory = _get_history_session_factory()
	async with session_factory() as session:
		yield session


def __getattr__(name: str):
	if name == "history_engine":
		return _get_history_engine()
	if name == "HistorySessionLocal":
		return _get_history_session_factory()
	raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["AsyncSession", "get_history_session", "ping_db"]
