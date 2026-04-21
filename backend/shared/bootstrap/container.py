"""Фабрика для создания инфраструктурного контейнера на основе APP_ENV."""

from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
	from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from ..config.base import BaseAppSettings
from ..config.database import DatabaseSettings, HistorySettings, MongoSettings
from ..config.rabbitmq import RabbitMQSettings

TSettings = TypeVar("TSettings", bound=BaseAppSettings)


class BootstrapContainer[TSettings: BaseAppSettings]:
	"""Контейнер инфраструктуры, инициализируемый при старте сервиса.

	Хранит настройки, движок БД и другие общие ресурсы.
	"""

	def __init__(self, settings: TSettings):
		self.settings = settings
		# Прокидываем APP_ENV во вложенные настройки для активации валидаторов
		self.settings.db.APP_ENV = self.settings.APP_ENV
		
		if self.settings.rabbitmq.URL:
			self.settings.rabbitmq.APP_ENV = self.settings.APP_ENV
		
		if self.settings.history.HOST:
			self.settings.history.APP_ENV = self.settings.APP_ENV
			
		if self.settings.mongo.URL:
			self.settings.mongo.APP_ENV = self.settings.APP_ENV

		self._engine: AsyncEngine | None = None
		self._session_factory: async_sessionmaker[AsyncSession] | None = None

		self._history_engine: AsyncEngine | None = None
		self._history_session_factory: async_sessionmaker[AsyncSession] | None = None

	@property
	def db_settings(self) -> DatabaseSettings:
		"""Использует настройки БД из общего объекта настроек."""
		return self.settings.db

	@property
	def rmq_settings(self) -> RabbitMQSettings:
		"""Использует настройки RabbitMQ из общего объекта настроек."""
		if not self.settings.rabbitmq.URL:
			raise RuntimeError("Настройки RabbitMQ не найдены в BaseAppSettings (RABBITMQ_URL не задан).")
		return self.settings.rabbitmq

	@property
	def history_settings(self) -> HistorySettings:
		"""Использует настройки истории (ClickHouse) из общего объекта настроек."""
		if not self.settings.history.HOST:
			raise RuntimeError("Настройки ClickHouse не найдены в BaseAppSettings (CLICKHOUSE_HOST не задан).")
		return self.settings.history

	@property
	def mongo_settings(self) -> MongoSettings:
		"""Использует настройки MongoDB из общего объекта настроек."""
		if not self.settings.mongo.URL:
			raise RuntimeError("Настройки MongoDB не найдены в BaseAppSettings (MONGO_URL не задан).")
		return self.settings.mongo

	@property
	def engine(self) -> "AsyncEngine":
		"""Ленивая инициализация движка БД."""
		if self._engine is None:
			self._engine = self._create_engine()
		return self._engine

	@property
	def session_factory(self) -> "async_sessionmaker[AsyncSession]":
		"""Ленивая инициализация фабрики сессий основной БД."""
		if self._session_factory is None:
			from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

			self._session_factory = async_sessionmaker(
				bind=self.engine,
				autoflush=False,
				expire_on_commit=False,
				class_=AsyncSession,
			)
		return self._session_factory

	@property
	def history_engine(self) -> "AsyncEngine":
		"""Ленивая инициализация движка БД истории (PostgreSQL)."""
		if self._history_engine is None:
			self._history_engine = self._create_engine(self.db_settings.HISTORY_DATABASE_URL)
		return self._history_engine

	@property
	def history_session_factory(self) -> "async_sessionmaker[AsyncSession]":
		"""Ленивая инициализация фабрики сессий БД истории."""
		if self._history_session_factory is None:
			from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

			self._history_session_factory = async_sessionmaker(
				bind=self.history_engine,
				autoflush=False,
				expire_on_commit=False,
				class_=AsyncSession,
			)
		return self._history_session_factory

	def _create_engine(self, url: str | None = None) -> "AsyncEngine":
		"""Создает движок SQLAlchemy с учетом пула соединений."""
		if url is None:
			url = self.db_settings.DATABASE_URL

		if not url:
			raise RuntimeError(
				"DATABASE_URL (или HISTORY_DATABASE_URL) не задан! Проверьте переменные окружения."
			)

		from sqlalchemy.ext.asyncio import create_async_engine

		return create_async_engine(
			url,
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
		if self._history_engine is not None:
			await self._history_engine.dispose()


_container: BootstrapContainer | None = None


def bootstrap[TSettings: BaseAppSettings](settings_class: type[TSettings]) -> BootstrapContainer[TSettings]:
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
