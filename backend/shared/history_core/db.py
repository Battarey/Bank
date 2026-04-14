"""Async-подключение к PostgreSQL History (engine, session factory)."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .env import HISTORY_DATABASE_URL

history_engine = create_async_engine(
	HISTORY_DATABASE_URL,
	pool_pre_ping=True,
	future=True,
)
HistorySessionLocal = async_sessionmaker(
	bind=history_engine,
	autoflush=False,
	expire_on_commit=False,
)


async def ping_db() -> bool:
	"""Проверить доступность базы данных истории."""
	async with history_engine.connect() as conn:
		await conn.execute(text("SELECT 1"))
		return True


async def get_history_session() -> AsyncGenerator[AsyncSession, None]:
	"""Асинхронная зависимость FastAPI, возвращающая сессию к postgres_history."""

	async with HistorySessionLocal() as session:
		yield session


__all__ = ["AsyncSession", "HistorySessionLocal", "engine", "get_history_session"]
