"""Async-подключение к PostgreSQL (engine, session factory)."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.bootstrap import get_container

# ВНИМАНИЕ: Эти функции требуют предварительного вызова bootstrap() в main.py
def _get_engine():
	return get_container().engine

def _get_session_factory():
	return get_container().session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
	"""Асинхронная зависимость FastAPI, возвращающая транзакционную сессию."""
	session_factory = _get_session_factory()
	async with session_factory() as session:
		yield session


async def ping_db() -> bool:
	"""Проверить доступность базы данных."""
	engine = _get_engine()
	async with engine.connect() as conn:
		await conn.execute(text("SELECT 1"))
		return True


def __getattr__(name: str):
	if name == "engine":
		return _get_engine()
	if name == "SessionLocal":
		return _get_session_factory()
	raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["AsyncSession", "get_session", "ping_db"]
