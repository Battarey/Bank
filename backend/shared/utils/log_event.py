"""Модуль для логирования событий (обратная совместимость)."""

from typing import Any
from ..rabbitmq.client import publish
from ..rabbitmq.constants import LOGS_EXCHANGE


async def log_event(routing_key: str, event_type: str, payload: dict[str, Any]) -> None:
	"""Отправляет событие в RabbitMQ для Log Service.
	
	Используется старыми сервисами, которые ещё не перешли на EDA/UoW.
	"""
	await publish(
		exchange_name=LOGS_EXCHANGE,
		routing_key=routing_key,
		body=payload,
	)
