"""Потребители сообщений RabbitMQ для Log Service."""

import asyncio
import json
import logging
import signal

import aio_pika

from shared.bootstrap import get_container
from shared.clickhouse_core import close_clickhouse, init_clickhouse
from shared.history_core import (
	history_engine,
)
from shared.history_core.models import HistoryBase

from .repository import ClickHouseRepository, PostgresHistoryRepository
from .schemas import LogEvent
from .service import LogService

logger = logging.getLogger("log_service.consumers")

MAX_RETRIES = 10
RETRY_DELAY = 3


async def _init_history_db() -> None:
	"""Создаёт необходимые таблицы в базе данных postgres_history при первом запуске."""
	async with history_engine.begin() as conn:
		await conn.run_sync(HistoryBase.metadata.create_all)
	logger.info("postgres_history: таблицы созданы / проверены.")


async def _process_message(
	message: aio_pika.abc.AbstractIncomingMessage,
	service: LogService,
) -> None:
	"""Обработка одного сообщения из очереди RabbitMQ.

	Args:
		message: Входящее сообщение от aio_pika.
		service: Экземпляр LogService для сохранения логов.
	"""
	async with message.process():
		try:
			data = json.loads(message.body)
		except json.JSONDecodeError:
			logger.error("Невалидный JSON: %s", message.body[:200])
			return

		try:
			event = LogEvent.model_validate(data)
			await service.process_log(event)
		except Exception as exc:
			logger.error("Ошибка валидации или записи лога: %s", exc)


async def _background_cleanup(repo: PostgresHistoryRepository) -> None:
	"""Фоновая задача для периодической очистки старых логов (TTL)."""
	while True:
		try:
			logger.info("Запуск плановой очистки старых логов...")
			deleted_count = await repo.delete_old_history(days=90)  # Срок хранения 90 дней
			if deleted_count > 0:
				logger.info("Очистка завершена: удалено %d записей.", deleted_count)
			else:
				logger.info("Очистка не требуется: старых записей не обнаружено.")
		except Exception as exc:
			logger.error("Ошибка при выполнении очистки логов: %s", exc)
		
		# Спим 24 часа перед следующей очисткой
		await asyncio.sleep(86400)


async def run_consumers() -> None:
	"""Запуск процесса потребления логов из RabbitMQ.

	Инициализирует подключение к Postgres History и ClickHouse, 
	создает репозитории и сервис обработки логов, затем начинает 
	прослушивание очереди RabbitMQ.
	"""
	# 1. Инициализация хранилищ
	await _init_history_db()
	await init_clickhouse()
	
	postgres_repo = PostgresHistoryRepository()
	clickhouse_repo = ClickHouseRepository()
	service = LogService(postgres_repo, clickhouse_repo)

	# 1.1 Запуск фоновой задачи очистки
	asyncio.create_task(_background_cleanup(postgres_repo))

	# 2. Подключение к RabbitMQ
	settings = get_container().settings
	logger.info("Подключение к RabbitMQ: %s", settings.RABBITMQ_URL)
	connection = None
	for attempt in range(1, MAX_RETRIES + 1):
		try:
			connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
			break
		except Exception as exc:
			logger.warning("Попытка %d/%d не удалась: %s", attempt, MAX_RETRIES, exc)
			if attempt == MAX_RETRIES:
				raise
			await asyncio.sleep(RETRY_DELAY)

	async with connection:
		channel = await connection.channel()
		await channel.set_qos(prefetch_count=10)

		exchange = await channel.declare_exchange(
			settings.LOGS_EXCHANGE,
			aio_pika.ExchangeType.TOPIC,
			durable=True,
		)

		queue = await channel.declare_queue(settings.LOG_QUEUE, durable=True)
		await queue.bind(exchange, settings.LOG_BINDING_KEY)

		logger.info("Слушаю очередь '%s' (binding: %s)", settings.LOG_QUEUE, settings.LOG_BINDING_KEY)
		await queue.consume(lambda msg: _process_message(msg, service))

		# Ожидание сигнала остановки
		stop_event = asyncio.Event()

		def _signal_handler() -> None:
			logger.info("Получен сигнал остановки.")
			stop_event.set()

		loop = asyncio.get_running_loop()
		for sig in (signal.SIGINT, signal.SIGTERM):
			try:
				loop.add_signal_handler(sig, _signal_handler)
			except NotImplementedError:
				pass

		await stop_event.wait()

	# 3. Очистка ресурсов
	await close_clickhouse()
	await history_engine.dispose()
	logger.info("Log service остановлен.")
