"""Типизированные хелперы для упрощения работы с RabbitMQ."""

from typing import Any
from uuid import UUID

from .client import publish
from .constants import (
	EMAIL_ROUTING_KEY,
	LOGS_EXCHANGE,
	NOTIFICATIONS_EXCHANGE,
)


async def send_notification(
	notification_type: str,
	to: str,
	variables: dict[str, Any] | None = None,
) -> None:
	"""Отправляет запрос на уведомление (Email).

	Args:
		notification_type: Тип шаблона (н-р, 'welcome', 'account_frozen').
		to: Email получателя.
		variables: Переменные для подстановки в шаблон.
	"""
	await publish(
		exchange_name=NOTIFICATIONS_EXCHANGE,
		routing_key=EMAIL_ROUTING_KEY,
		body={
			"type": notification_type,
			"payload": {
				"to": to,
				"variables": variables or {},
			},
		},
	)


async def send_log(
	routing_key: str,
	user_id: UUID | str,
	action: str,
	service: str,
	status: str = "success",
	details: str = "",
	**kwargs,
) -> None:
	"""Отправляет бизнес-событие в систему логирования.

	Args:
		routing_key: Ключ маршрутизации (н-р, LOG_ACCOUNT_KEY).
		user_id: ID пользователя, инициировавшего действие.
		action: Название действия (н-р, 'create_account').
		service: Имя сервиса-источника.
		status: Статус операции ('success', 'failure', 'pending').
		details: Описание или причина ошибки.
		**kwargs: Дополнительные поля для лога.
	"""
	payload = {
		"user_id": str(user_id),
		"action": action,
		"service": service,
		"status": status,
		"details": details,
		**kwargs,
	}
	body = {
		"type": "log_event",
		"payload": payload,
	}
	await publish(
		exchange_name=LOGS_EXCHANGE,
		routing_key=routing_key,
		body=body,
	)
