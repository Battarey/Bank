"""Async-подключение к PostgreSQL History (engine, session factory)."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .env import HISTORY_DATABASE_URL

engine = create_async_engine(HISTORY_DATABASE_URL, future=True)
HistorySessionLocal = async_sessionmaker(
	bind=engine,
	autoflush=False,
	expire_on_commit=False,
)


async def get_history_session() -> AsyncGenerator[AsyncSession, None]:
	"""Асинхронная зависимость FastAPI, возвращающая сессию к postgres_history."""

	async with HistorySessionLocal() as session:
		yield session


__all__ = ["AsyncSession", "HistorySessionLocal", "engine", "get_history_session"]
