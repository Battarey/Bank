from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .env import POSTGRES_CORE_DATABASE_URL

engine = create_async_engine(POSTGRES_CORE_DATABASE_URL, future=True)
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
