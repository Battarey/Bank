"""ORM-модель транзакции (операции по банковскому счёту)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Transaction(Base):
	"""Операция по банковскому счёту: пополнение, снятие, перевод."""

	__tablename__ = "transactions"

	id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
	account_id: Mapped[UUID] = mapped_column(
		PGUUID(as_uuid=True),
		ForeignKey("bank_accounts.id", ondelete="CASCADE"),
		nullable=False,
		index=True,
	)
	type: Mapped[str] = mapped_column(Text, nullable=False)
	amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	related_account_id: Mapped[UUID | None] = mapped_column(
		PGUUID(as_uuid=True),
		ForeignKey("bank_accounts.id", ondelete="SET NULL"),
		nullable=True,
	)
	direction: Mapped[str] = mapped_column(Text, nullable=False)
	status: Mapped[str] = mapped_column(Text, nullable=False)
	balance_before: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
	balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
	external_ref: Mapped[str | None] = mapped_column(Text, nullable=True)


__all__ = ["Transaction"]
