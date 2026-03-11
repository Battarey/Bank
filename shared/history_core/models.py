"""ORM-модели для postgres_history — аудит-лог действий пользователя."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class HistoryBase(DeclarativeBase):
	"""Базовый класс для моделей postgres_history."""
	pass


class UserAction(HistoryBase):
	"""Аудит-лог действий пользователя.

	Хранит все значимые события: вход, смена PIN, операции со счетами,
	транзакции, блокировки и т.д.
	"""

	__tablename__ = "user_actions"

	id: Mapped[uuid.UUID] = mapped_column(
		PGUUID(as_uuid=True),
		primary_key=True,
		default=uuid.uuid4,
	)

	# Кто выполнил действие
	user_id: Mapped[uuid.UUID] = mapped_column(
		PGUUID(as_uuid=True),
		nullable=False,
		index=True,
	)

	# Тип действия (login, logout, set_pin, open_account, close_account,
	# freeze_account, unfreeze_account, deposit, withdrawal, transfer,
	# self_block, unlock, registration и т.д.)
	action: Mapped[str] = mapped_column(Text, nullable=False, index=True)

	# Источник события (имя сервиса)
	service: Mapped[str] = mapped_column(Text, nullable=False)

	# Произвольные детали действия (JSON-friendly текст)
	details: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Связанный объект (например, account_id или transaction_id)
	entity_id: Mapped[uuid.UUID | None] = mapped_column(
		PGUUID(as_uuid=True),
		nullable=True,
		index=True,
	)

	# Тип связанного объекта (account, transaction)
	entity_type: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Сумма (для финансовых операций)
	amount: Mapped[float | None] = mapped_column(
		Numeric(18, 2),
		nullable=True,
	)

	# Валюта (для финансовых операций)
	currency: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Результат действия (success, failed, blocked)
	status: Mapped[str] = mapped_column(Text, nullable=False, default="success")

	# IP-адрес (если передаётся через gateway)
	ip_address: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Когда произошло
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		nullable=False,
		server_default=text("now()"),
		index=True,
	)

	def __repr__(self) -> str:
		return (
			f"<UserAction(id={self.id}, user_id={self.user_id}, "
			f"action={self.action!r}, status={self.status!r})>"
		)
