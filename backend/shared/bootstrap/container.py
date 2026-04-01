"""Фабрика для создания инфраструктурного контейнера на основе APP_ENV."""

from typing import Type, TypeVar, Generic, Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine, AsyncEngine
from ..config.base import BaseAppSettings
from ..config.database import DatabaseSettings
from ..config.rabbitmq import RabbitMQSettings

TSettings = TypeVar("TSettings", bound=BaseAppSettings)


class BootstrapContainer(Generic[TSettings]):
	"""Контейнер инфраструктуры, инициализируемый при старте сервиса.
	
	Хранит настройки, движок БД и другие общие ресурсы.
	"""

	def __init__(self, settings: TSettings):
		self.settings = settings
		
		# Настройки БД (если есть)
		self.db_settings = DatabaseSettings()
		self.rmq_settings = RabbitMQSettings()
		
		# Инициализация SQLAlchemy Engine
		self.engine: AsyncEngine = self._create_engine()
		self.session_factory = async_sessionmaker(
			bind=self.engine,
			autoflush=False,
			expire_on_commit=False,
			class_=AsyncSession,
		)

	def _create_engine(self) -> AsyncEngine:
		"""Создает движок SQLAlchemy с учетом пула соединений."""
		return create_async_engine(
			self.db_settings.DATABASE_URL,
			pool_size=self.db_settings.DB_POOL_SIZE,
			max_overflow=self.db_settings.DB_MAX_OVERFLOW,
			pool_recycle=self.db_settings.DB_POOL_RECYCLE,
			pool_pre_ping=True,
			future=True,
		)

	async def dispose(self) -> None:
		"""Закрывает все соединения при остановке приложения."""
		await self.engine.dispose()


_container: BootstrapContainer | None = None


def bootstrap(settings_class: Type[TSettings]) -> BootstrapContainer[TSettings]:
	"""Инициализирует глобальный контейнер настроек и ресурсов.
	
	Должен вызываться один раз при старте приложения (main.py).
	"""
	global _container
	if _container is None:
		settings = settings_class()
		_container = BootstrapContainer(settings)
	return _container


def get_container() -> BootstrapContainer:
	"""Возвращает текущий инициализированный контейнер."""
	if _container is None:
		raise RuntimeError("Bootstrap не был выполнен! Вызовите bootstrap() при старте.")
	return _container
