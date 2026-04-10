"""Репозитории для сохранения логов в PostgreSQL и ClickHouse."""

import logging
from uuid import uuid4

from sqlalchemy import delete

from shared.clickhouse_core import insert_log_event
from shared.history_core import (
	HistorySessionLocal,
	UserAction,
)

from .schemas import LogPayload

logger = logging.getLogger("log_service")


class PostgresHistoryRepository:
	"""Репозиторий для аудит-лога в PostgreSQL."""

	async def save_action(self, payload: LogPayload) -> None:
		"""Сохраняет действие пользователя в postgres_history."""

		# Если user_id нет (системный лог), в аудит-лог пользователя не пишем
		if not payload.user_id:
			return

		action_record = UserAction(
			id=uuid4(),
			user_id=payload.user_id,
			action=payload.action,
			service=payload.service,
			details=payload.details,
			entity_id=payload.entity_id,
			entity_type=payload.entity_type,
			amount=payload.amount,
			currency=payload.currency,
			status=payload.status,
			ip_address=payload.ip_address,
			created_at=payload.created_at,
		)

		async with HistorySessionLocal() as session:
			session.add(action_record)
			await session.commit()

	async def delete_old_history(self, days: int) -> int:
		"""Удаляет записи истории старше N дней.

		Модель UserAction имеет поле created_at.
		"""
		from datetime import UTC, datetime, timedelta

		cutoff = datetime.now(UTC) - timedelta(days=days)

		stmt = delete(UserAction).where(UserAction.created_at < cutoff)

		async with HistorySessionLocal() as session:
			result = await session.execute(stmt)
			await session.commit()
			return result.rowcount


class ClickHouseRepository:
	"""Репозиторий для аналитических логов в ClickHouse."""

	async def save_event(self, event_type: str, payload: LogPayload) -> None:
		"""Сохраняет событие в ClickHouse."""

		await insert_log_event(
			event_type=event_type,
			service=payload.service,
			user_id=str(payload.user_id) if payload.user_id else "00000000-0000-0000-0000-000000000000",
			action=payload.action,
			entity_id=str(payload.entity_id) if payload.entity_id else None,
			entity_type=payload.entity_type,
			amount=payload.amount,
			currency=payload.currency,
			status=payload.status,
			details=payload.details,
			ip_address=payload.ip_address,
			created_at=payload.created_at,
		)
