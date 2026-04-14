"""Асинхронный клиент RabbitMQ (aio-pika): подключение, публикация сообщений."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import aio_pika

logger = logging.getLogger(__name__)

RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

_connection: aio_pika.abc.AbstractRobustConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None

MAX_RETRIES = 10
RETRY_DELAY = 3  # секунды


async def connect() -> None:
	"""Установить соединение и открыть канал с retry-логикой."""
	global _connection, _channel

	for attempt in range(1, MAX_RETRIES + 1):
		try:
			_connection = await aio_pika.connect_robust(RABBITMQ_URL)
			_channel = await _connection.channel()
			logger.info("RabbitMQ connected: %s", RABBITMQ_URL)
			return
		except Exception as exc:
			logger.warning(
				"RabbitMQ connection attempt %d/%d failed: %s. Retry in %ds...",
				attempt,
				MAX_RETRIES,
				exc,
				RETRY_DELAY,
			)
			if attempt == MAX_RETRIES:
				raise
			await asyncio.sleep(RETRY_DELAY)


async def disconnect() -> None:
	"""Закрыть канал и соединение."""
	global _connection, _channel

	if _channel and not _channel.is_closed:
		await _channel.close()
	if _connection and not _connection.is_closed:
		await _connection.close()
	_connection = None
	_channel = None
	logger.info("RabbitMQ disconnected.")


async def publish(
	exchange_name: str,
	routing_key: str,
	body: dict[str, Any],
) -> None:
	"""Опубликовать JSON-сообщение в указанный exchange.

	Raises RuntimeError если соединение не установлено.
	"""
	if _channel is None:
		raise RuntimeError("RabbitMQ не подключён. Вызовите connect() при старте.")

	exchange = await _channel.declare_exchange(
		exchange_name,
		aio_pika.ExchangeType.TOPIC,
		durable=True,
	)

	message = aio_pika.Message(
		body=json.dumps(body, ensure_ascii=False).encode(),
		content_type="application/json",
		delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
	)

	await exchange.publish(message, routing_key=routing_key)
	logger.debug("Published %s → %s: %s", exchange_name, routing_key, body.get("type"))


async def ping_rabbitmq() -> bool:
	"""Проверить доступность RabbitMQ."""
	if _connection is None or _connection.is_closed:
		return False
	if _channel is None or _channel.is_closed:
		return False
	return True


__all__ = ["connect", "disconnect", "ping_rabbitmq", "publish"]
