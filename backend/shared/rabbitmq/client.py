"""Асинхронный клиент RabbitMQ (aio-pika): подключение, публикация сообщений."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aio_pika

from shared.bootstrap import get_container

logger = logging.getLogger(__name__)

async def connect(url: str | None = None) -> None:
	"""Установить соединение и открыть канал с retry-логикой.

	Результаты сохраняются в BootstrapContainer.
	"""
	container = get_container()
	settings = container.rmq_settings

	if url is None:
		url = settings.URL

	max_retries = settings.MAX_RETRIES
	retry_delay = settings.RETRY_DELAY

	for attempt in range(1, max_retries + 1):
		try:
			container._rmq_connection = await aio_pika.connect_robust(url)
			container._rmq_channel = await container._rmq_connection.channel()
			logger.info("RabbitMQ connected: %s", url)
			return
		except Exception as exc:
			logger.warning(
				"RabbitMQ connection attempt %d/%d failed: %s. Retry in %ds...",
				attempt,
				max_retries,
				exc,
				retry_delay,
			)
			if attempt == max_retries:
				raise
			await asyncio.sleep(retry_delay)


async def disconnect() -> None:
	"""Закрыть канал и соединение через контейнер."""
	container = get_container()

	if container._rmq_channel and not container._rmq_channel.is_closed:
		await container._rmq_channel.close()
	if container._rmq_connection and not container._rmq_connection.is_closed:
		await container._rmq_connection.close()

	container._rmq_connection = None
	container._rmq_channel = None
	container._rmq_exchanges.clear()
	logger.info("RabbitMQ disconnected.")


async def publish(
	exchange_name: str,
	routing_key: str,
	body: dict[str, Any],
) -> None:
	"""Опубликовать JSON-сообщение в указанный exchange (с кэшированием)."""
	container = get_container()
	channel = container._rmq_channel

	if channel is None:
		raise RuntimeError("RabbitMQ не подключён. Вызовите connect() при старте.")

	# Кэширование exchange для избежания повторных деклараций
	if exchange_name not in container._rmq_exchanges:
		container._rmq_exchanges[exchange_name] = await channel.declare_exchange(
			exchange_name,
			aio_pika.ExchangeType.TOPIC,
			durable=True,
		)

	exchange = container._rmq_exchanges[exchange_name]

	message = aio_pika.Message(
		body=json.dumps(body, ensure_ascii=False).encode(),
		content_type="application/json",
		delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
	)

	await exchange.publish(message, routing_key=routing_key)
	logger.debug("Published %s → %s: %s", exchange_name, routing_key, body.get("type"))


async def ping_rabbitmq() -> bool:
	"""Проверить доступность RabbitMQ через контейнер."""
	container = get_container()
	conn = container._rmq_connection
	chan = container._rmq_channel

	if conn is None or conn.is_closed:
		return False
	if chan is None or chan.is_closed:
		return False
	return True


__all__ = ["connect", "disconnect", "ping_rabbitmq", "publish"]
