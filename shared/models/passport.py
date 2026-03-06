"""ORM-модель паспортных данных."""

from datetime import date
from uuid import UUID
from sqlalchemy import Date, ForeignKey, Text, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Passport(Base):
	"""Паспортные данные клиента."""

	__tablename__ = "passport"

	client_id: Mapped[UUID] = mapped_column(
		PGUUID(as_uuid=True),
		ForeignKey("users.id", ondelete="CASCADE"),
		primary_key=True,
		nullable=False,
	)
	series: Mapped[str] = mapped_column(String(4), nullable=False)
	number: Mapped[str] = mapped_column(String(6), nullable=False)
	division_code: Mapped[str] = mapped_column(String(7), nullable=False)
	issued_by: Mapped[str] = mapped_column(Text, nullable=False)
	issued_at: Mapped[date] = mapped_column(Date, nullable=False)
	expiration_date: Mapped[date] = mapped_column(Date, nullable=False)
	registration_address: Mapped[str] = mapped_column(Text, nullable=False)

__all__ = ["Passport"]
