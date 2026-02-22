from uuid import UUID
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class Contact(Base):
	"""Контактные данные клиента."""

	__tablename__ = "contacts"

	client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, nullable=False)
	email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
	phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)

__all__ = ["Contact"]
