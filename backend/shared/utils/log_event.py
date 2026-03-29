"""Хелпер для единообразной отправки событий бизнес-логирования."""

from typing import Any, Dict
import logging

from shared.rabbitmq.client import publish
from shared.rabbitmq.constants import LOGS_EXCHANGE

logger = logging.getLogger(__name__)


async def log_event(
	routing_key: str,
	event_type: str,
	payload: Dict[str, Any],
) -> None:
	"""Отправляет бизнес-событие в RabbitMQ для аналитики и аудита.

	Это вспомогательная операция. Ошибки при отправке логов не должны
	прерывать выполнение основной бизнес-логики.

	Args:
		routing_key: Ключ маршрутизации (например, LOG_AUTH_KEY).
		event_type: Тип события (например, "auth", "account").
		payload: Данные события.
	"""

	body = {
		"type": event_type,
		"payload": payload,
	}

	try:
		await publish(
			exchange_name=LOGS_EXCHANGE,
			routing_key=routing_key,
			body=body,
		)
	except Exception as exc:
		logger.warning("Не удалось отправить бизнес-лог в RabbitMQ: %s", exc)
