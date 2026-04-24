"""Async-подключение к PostgreSQL (engine, session factory)."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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
engine = InfrastructureProxy("engine")
SessionLocal = InfrastructureProxy("session_factory")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
	"""Асинхронная зависимость FastAPI, возвращающая транзакционную сессию."""
	async with SessionLocal() as session:
		yield session


async def ping_db() -> bool:
	"""Проверить доступность базы данных."""
	async with engine.connect() as conn:
		await conn.execute(text("SELECT 1"))
		return True


__all__ = ["AsyncSession", "SessionLocal", "engine", "get_session", "ping_db"]
