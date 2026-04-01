"""Фабрика для создания инфраструктурного контейнера на основе APP_ENV."""

from typing import Type, TypeVar, Generic, Any, TYPE_CHECKING
if TYPE_CHECKING:
	from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, AsyncEngine

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
		
		self._db_settings: DatabaseSettings | None = None
		self._rmq_settings: RabbitMQSettings | None = None
		self._engine: 'AsyncEngine | None' = None
		self._session_factory: 'async_sessionmaker[AsyncSession] | None' = None

	@property
	def db_settings(self) -> DatabaseSettings:
		"""Ленивая инициализация настроек БД."""
		if self._db_settings is None:
			self._db_settings = DatabaseSettings()
		return self._db_settings

	@property
	def rmq_settings(self) -> RabbitMQSettings:
		"""Ленивая инициализация настроек RabbitMQ."""
		if self._rmq_settings is None:
			self._rmq_settings = RabbitMQSettings()
		return self._rmq_settings

	@property
	def engine(self) -> 'AsyncEngine':
		"""Ленивая инициализация движка БД."""
		if self._engine is None:
			self._engine = self._create_engine()
		return self._engine

	@property
	def session_factory(self) -> 'async_sessionmaker[AsyncSession]':
		"""Ленивая инициализация фабрики сессий."""
		if self._session_factory is None:
			from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
			self._session_factory = async_sessionmaker(
				bind=self.engine,
				autoflush=False,
				expire_on_commit=False,
				class_=AsyncSession,
			)
		return self._session_factory

	def _create_engine(self) -> 'AsyncEngine':
		"""Создает движок SQLAlchemy с учетом пула соединений."""
		from sqlalchemy.ext.asyncio import create_async_engine
		return create_async_engine(
			self.db_settings.DATABASE_URL,
			pool_size=self.db_settings.DB_POOL_SIZE,
			max_overflow=self.db_settings.DB_MAX_OVERFLOW,
			pool_recycle=self.db_settings.DB_POOL_RECYCLE,
			pool_pre_ping=True,
			future=True,
		)

	async def dispose(self) -> None:
		"""Закрывает все соединения при остановке приложения (если они были открыты)."""
		if self._engine is not None:
			await self._engine.dispose()


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
