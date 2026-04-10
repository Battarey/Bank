"""Async-подключение к PostgreSQL (engine, session factory)."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .env import (
	DB_MAX_OVERFLOW,
	DB_POOL_RECYCLE,
	DB_POOL_SIZE,
	POSTGRES_CORE_DATABASE_URL,
)

engine = create_async_engine(
	POSTGRES_CORE_DATABASE_URL,
	pool_size=DB_POOL_SIZE,
	max_overflow=DB_MAX_OVERFLOW,
	pool_recycle=DB_POOL_RECYCLE,
	pool_pre_ping=True,
	future=True,
)
SessionLocal = async_sessionmaker(
	bind=engine,
	autoflush=False,
	expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
	"""Асинхронная зависимость FastAPI, возвращающая транзакционную сессию."""

	async with SessionLocal() as session:
		yield session


__all__ = ["AsyncSession", "engine", "get_session", "SessionLocal"]
