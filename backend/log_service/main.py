"""Log Service — потребитель RabbitMQ, запись бизнес-событий.

Слушает очередь log_queue и записывает события в ClickHouse (аналитика)
и PostgreSQL History (аудит-лог пользователя).
Не является HTTP-сервисом — работает как воркер.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from datetime import datetime, timezone
from uuid import UUID, uuid4

import aio_pika
from .repository import PostgresHistoryRepository, ClickHouseRepository
from .schemas import LogEvent
from .service import LogService

from shared.clickhouse_core import close_clickhouse, init_clickhouse
from shared.history_core import (
	history_engine,
)
from shared.history_core.models import HistoryBase

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("log_service")

RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

EXCHANGE_NAME = "logs"
QUEUE_NAME = "log_queue"
BINDING_KEY = "log.#"

MAX_RETRIES = 10
RETRY_DELAY = 3  # секунды


async def _init_history_db() -> None:
	"""Создаёт таблицы в postgres_history при первом запуске."""

	async with history_engine.begin() as conn:
		await conn.run_sync(HistoryBase.metadata.create_all)
	logger.info("postgres_history: таблицы созданы / проверены.")


async def _process_message(
	message: aio_pika.abc.AbstractIncomingMessage,
	service: LogService,
) -> None:
	"""Обработка одного сообщения из очереди."""

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


async def run() -> None:
	"""Основной цикл: подключение к хранилищам и потребление сообщений."""

	# ── Инициализация хранилищ ─────────────────────────────────────────
	await _init_history_db()
	await init_clickhouse()
	
	postgres_repo = PostgresHistoryRepository()
	clickhouse_repo = ClickHouseRepository()
	service = LogService(postgres_repo, clickhouse_repo)

	# ── RabbitMQ ───────────────────────────────────────────────────────
	logger.info("Подключение к RabbitMQ: %s", RABBITMQ_URL)

	for attempt in range(1, MAX_RETRIES + 1):
		try:
			connection = await aio_pika.connect_robust(RABBITMQ_URL)
			break
		except Exception as exc:
			logger.warning(
				"RabbitMQ attempt %d/%d failed: %s. Retry in %ds...",
				attempt, MAX_RETRIES, exc, RETRY_DELAY,
			)
			if attempt == MAX_RETRIES:
				raise
			await asyncio.sleep(RETRY_DELAY)

	async with connection:
		channel = await connection.channel()
		await channel.set_qos(prefetch_count=10)

		exchange = await channel.declare_exchange(
			EXCHANGE_NAME,
			aio_pika.ExchangeType.TOPIC,
			durable=True,
		)

		queue = await channel.declare_queue(QUEUE_NAME, durable=True)
		await queue.bind(exchange, BINDING_KEY)

		logger.info("Слушаю очередь '%s' (binding: %s)", QUEUE_NAME, BINDING_KEY)
		await queue.consume(lambda msg: _process_message(msg, service))

		# Ждём сигнала остановки
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

	# ── Cleanup ────────────────────────────────────────────────────────
	await close_clickhouse()
	await history_engine.dispose()

	logger.info("Log service остановлен.")


def main() -> None:
	"""Entry point."""
	try:
		asyncio.run(run())
	except KeyboardInterrupt:
		logger.info("Прервано пользователем.")


if __name__ == "__main__":
	main()
