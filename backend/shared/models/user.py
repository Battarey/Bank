"""ORM-модель пользователя."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class User(Base):
	"""Запись клиента банковского сервиса."""

	__tablename__ = "users"

	id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
	is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
	pin_hash: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)


__all__ = ["User"]
