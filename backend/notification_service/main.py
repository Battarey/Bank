"""Notification Service — потребитель RabbitMQ, отправка email.

Слушает очередь email_queue и отправляет письма через SMTP.
Не является HTTP-сервисом — работает как воркер.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal

import aio_pika

from .repository import NotificationRepository
from .schemas import NotificationTask
from .service import NotificationService
from .store import close_mongo, init_mongo

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("notification_service")

RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

EXCHANGE_NAME = "notifications"
QUEUE_NAME = "email_queue"
BINDING_KEY = "email.#"


async def _process_message(
	message: aio_pika.abc.AbstractIncomingMessage, 
	service: NotificationService,
) -> None:
	"""Обработка одного сообщения из очереди."""

	async with message.process():
		try:
			data = json.loads(message.body)
		except json.JSONDecodeError:
			logger.error("Невалидный JSON: %s", message.body[:200])
			return

		try:
			# Валидация входных данных через Pydantic
			task = NotificationTask.model_validate(data)
			await service.process_notification(task)
		except Exception as exc:
			logger.error("Ошибка валидации или обработки сообщения: %s", exc)


MAX_RETRIES = 10
RETRY_DELAY = 3  # секунды


async def run() -> None:
	"""Основной цикл: подключение к RabbitMQ и потребление сообщений."""

	# ── MongoDB ────────────────────────────────────────────────────────
	await init_mongo()
	repository = NotificationRepository()
	service = NotificationService(repository)

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
		
		# Передаем сервис в обработчик через лямбду или partial
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
				# Windows не поддерживает add_signal_handler
				pass

		await stop_event.wait()

	# ── Cleanup ────────────────────────────────────────────────────────
	await close_mongo()

	logger.info("Notification service остановлен.")


def main() -> None:
	"""Entry point."""
	try:
		asyncio.run(run())
	except KeyboardInterrupt:
		logger.info("Прервано пользователем.")


if __name__ == "__main__":
	main()
