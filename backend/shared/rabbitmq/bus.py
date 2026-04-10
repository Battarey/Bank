"""Message Bus для трансляции Domain Events в RabbitMQ."""

import logging

from shared.events.base import BaseEvent, LogEvent, NotificationEvent
from shared.rabbitmq.constants import (
	LOG_ACCOUNT_KEY,
	LOG_AUTH_KEY,
	LOG_TRANSACTION_KEY,
)
from shared.rabbitmq.helpers import send_log, send_notification

logger = logging.getLogger("shared.events")


class MessageBus:
	"""Шина событий, отвечающая за публикацию событий в RabbitMQ."""

	@staticmethod
	async def handle(events: list[BaseEvent]) -> None:
		"""Обрабатывает список событий, отправляя их в RabbitMQ."""
		for event in events:
			try:
				await MessageBus._publish(event)
			except Exception as exc:
				logger.error("Ошибка при публикации события %s: %s", type(event).__name__, exc)

	@staticmethod
	async def _publish(event: BaseEvent) -> None:
		"""Логика публикации конкретного события."""

		if isinstance(event, NotificationEvent):
			await send_notification(
				notification_type=event.type,
				to=event.to,
				variables=event.variables,
			)

		elif isinstance(event, LogEvent):
			routing_key = MessageBus._get_routing_key(event)
			await send_log(
				routing_key=routing_key,
				user_id=event.user_id or "system",
				action=event.action,
				service=event.service,
				status=event.status,
				details=event.details or "",
				entity_id=event.entity_id,
				entity_type=event.entity_type,
				amount=event.amount,
				currency=event.currency,
			)

	@staticmethod
	def _get_routing_key(event: LogEvent) -> str:
		"""Определяет routing_key на основе сервиса-источника."""
		service = event.service.lower()
		if "auth" in service:
			return LOG_AUTH_KEY
		if "account" in service:
			return LOG_ACCOUNT_KEY
		if "transaction" in service or "transfer" in service:
			return LOG_TRANSACTION_KEY

		return "log.general"
