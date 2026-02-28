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

from .smtp import send_email
from .templates import get_template

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("notification_service")

RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

EXCHANGE_NAME = "notifications"
QUEUE_NAME = "email_queue"
BINDING_KEY = "email.#"


async def _process_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
	"""Обработка одного сообщения из очереди."""

	async with message.process():
		try:
			data = json.loads(message.body)
		except json.JSONDecodeError:
			logger.error("Невалидный JSON: %s", message.body[:200])
			return

		msg_type: str = data.get("type", "")
		payload: dict = data.get("payload", {})

		logger.info("Получено сообщение: type=%s", msg_type)

		try:
			template = get_template(msg_type)
			subject, body = template.render(payload.get("variables", {}))

			await send_email(
				to=payload["to"],
				subject=subject,
				body=body,
			)
			logger.info("%s → %s", msg_type, payload["to"])

		except ValueError:
			logger.warning("Неизвестный шаблон: %s", msg_type)
		except KeyError as exc:
			logger.error("Не хватает переменной для шаблона %s: %s", msg_type, exc)
		except Exception:
			logger.exception("Ошибка обработки сообщения type=%s", msg_type)


MAX_RETRIES = 10
RETRY_DELAY = 3  # секунды


async def run() -> None:
	"""Основной цикл: подключение к RabbitMQ и потребление сообщений."""

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
				# Windows не поддерживает add_signal_handler
				pass

		await stop_event.wait()

	logger.info("Notification service остановлен.")


def main() -> None:
	"""Entry point."""
	try:
		asyncio.run(run())
	except KeyboardInterrupt:
		logger.info("Прервано пользователем.")


if __name__ == "__main__":
	main()
