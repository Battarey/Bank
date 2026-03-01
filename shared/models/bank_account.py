from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CHAR, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BankAccount(Base):
	"""Банковский счёт клиента."""

	__tablename__ = "bank_accounts"

	id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
	client_id: Mapped[UUID] = mapped_column(
		PGUUID(as_uuid=True),
		ForeignKey("users.id", ondelete="CASCADE"),
		nullable=False,
	)
	account_number: Mapped[str] = mapped_column(CHAR(20), nullable=False, unique=True)
	type: Mapped[str] = mapped_column(Text, nullable=False)
	currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
	balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
	status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
	opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = ["BankAccount"]
