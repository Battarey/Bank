"""Асинхронный клиент RabbitMQ (aio-pika): подключение, публикация сообщений."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aio_pika

from shared.bootstrap import get_container

logger = logging.getLogger(__name__)

_connection: aio_pika.abc.AbstractRobustConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None


async def connect(url: str | None = None) -> None:
	"""Установить соединение и открыть канал с retry-логикой.

	Если url не указан, берется из глобального контейнера настроек.
	"""
	global _connection, _channel

	settings = get_container().rmq_settings
	if url is None:
		url = settings.URL

	max_retries = settings.MAX_RETRIES
	retry_delay = settings.RETRY_DELAY

	for attempt in range(1, max_retries + 1):
		try:
			_connection = await aio_pika.connect_robust(url)
			_channel = await _connection.channel()
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
