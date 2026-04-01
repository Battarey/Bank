"""Потребители сообщений RabbitMQ для Notification Service."""

import asyncio
import json
import logging
import os
import signal
import aio_pika

from shared.bootstrap import get_container
from .repository import NotificationRepository
from .schemas import NotificationTask
from .service import NotificationService
from .store import close_mongo, init_mongo

logger = logging.getLogger("notification_service.consumers")

MAX_RETRIES = 10
RETRY_DELAY = 3


async def _process_message(
	message: aio_pika.abc.AbstractIncomingMessage, 
	service: NotificationService,
) -> None:
	"""Обработка одного сообщения из очереди RabbitMQ.

	Args:
		message: Входящее сообщение от aio_pika.
		service: Экземпляр NotificationService для бизнес-логики.
	"""
	async with message.process():
		try:
			data = json.loads(message.body)
		except json.JSONDecodeError:
			logger.error("Невалидный JSON: %s", message.body[:200])
			return

		try:
			task = NotificationTask.model_validate(data)
			await service.process_notification(task)
		except Exception as exc:
			logger.error("Ошибка валидации или обработки сообщения: %s", exc)


async def run_consumers() -> None:
	"""Запуск процесса потребления сообщений из RabbitMQ.

	Инициализирует подключение к MongoDB, создаёт репозиторий и сервис, 
	затем устанавливает соединение с очередью и начинает прослушивание.
	"""
	# 1. Инициализация слоев
	settings = get_container().settings
	await init_mongo(settings.MONGO_URL)
	repository = NotificationRepository()
	service = NotificationService(repository)

	# 2. Подключение к RabbitMQ
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
			settings.NOTIFICATIONS_EXCHANGE,
			aio_pika.ExchangeType.TOPIC,
			durable=True,
		)

		queue = await channel.declare_queue(settings.EMAIL_QUEUE, durable=True)
		await queue.bind(exchange, settings.EMAIL_BINDING_KEY)

		logger.info("Слушаю очередь '%s' (binding: %s)", settings.EMAIL_QUEUE, settings.EMAIL_BINDING_KEY)
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
	await close_mongo()
	logger.info("Потребители остановлены.")
