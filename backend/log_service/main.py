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
from sqlalchemy.ext.asyncio import AsyncSession

from shared.clickhouse_core import close_clickhouse, init_clickhouse, insert_log_event
from shared.history_core import (
	HistorySessionLocal,
	UserAction,
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


async def _save_to_history(data: dict) -> None:
	"""Сохраняет событие в postgres_history (аудит-лог)."""

	payload = data.get("payload", {})
	user_id_str = payload.get("user_id")

	if not user_id_str:
		logger.warning("Пропуск записи в history: нет user_id. data=%s", data)
		return

	try:
		user_id = UUID(user_id_str)
	except (ValueError, TypeError):
		logger.warning("Невалидный user_id: %s", user_id_str)
		return

	entity_id = None
	entity_id_str = payload.get("entity_id")
	if entity_id_str:
		try:
			entity_id = UUID(entity_id_str)
		except (ValueError, TypeError):
			pass

	action_record = UserAction(
		id=uuid4(),
		user_id=user_id,
		action=payload.get("action", data.get("type", "unknown")),
		service=payload.get("service", "unknown"),
		details=payload.get("details"),
		entity_id=entity_id,
		entity_type=payload.get("entity_type"),
		amount=payload.get("amount"),
		currency=payload.get("currency"),
		status=payload.get("status", "success"),
		ip_address=payload.get("ip_address"),
		created_at=datetime.now(timezone.utc),
	)

	async with HistorySessionLocal() as session:
		session.add(action_record)
		await session.commit()


async def _save_to_clickhouse(data: dict) -> None:
	"""Сохраняет событие в ClickHouse (аналитика)."""

	payload = data.get("payload", {})
	event_type = data.get("type", "unknown")

	await insert_log_event(
		event_type=event_type,
		service=payload.get("service", "unknown"),
		user_id=payload.get("user_id", "00000000-0000-0000-0000-000000000000"),
		action=payload.get("action", event_type),
		entity_id=payload.get("entity_id"),
		entity_type=payload.get("entity_type"),
		amount=payload.get("amount"),
		currency=payload.get("currency"),
		status=payload.get("status", "success"),
		details=payload.get("details"),
		ip_address=payload.get("ip_address"),
		created_at=payload.get("created_at"),
	)


async def _process_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
	"""Обработка одного сообщения из очереди."""

	async with message.process():
		try:
			data = json.loads(message.body)
		except json.JSONDecodeError:
			logger.error("Невалидный JSON: %s", message.body[:200])
			return

		msg_type: str = data.get("type", "")
		logger.info("Получено событие: type=%s", msg_type)

		# Записываем параллельно в оба хранилища
		results = await asyncio.gather(
			_save_to_history(data),
			_save_to_clickhouse(data),
			return_exceptions=True,
		)

		for i, result in enumerate(results):
			if isinstance(result, Exception):
				store_name = "postgres_history" if i == 0 else "ClickHouse"
				logger.exception(
					"Ошибка записи в %s для type=%s: %s",
					store_name, msg_type, result,
				)


async def run() -> None:
	"""Основной цикл: подключение к хранилищам и потребление сообщений."""

	# ── Инициализация хранилищ ─────────────────────────────────────────
	await _init_history_db()
	await init_clickhouse()

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
		await queue.consume(_process_message)

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
