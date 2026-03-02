"""ORM-модель идентификаторов (ИНН, СНИЛС)."""

from uuid import UUID
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class Identifier(Base):
	"""Идентификаторы налогоплательщика и социального страхования."""

	__tablename__ = "identifiers"

	client_id: Mapped[UUID] = mapped_column(
		PGUUID(as_uuid=True),
		ForeignKey("users.id", ondelete="CASCADE"),
		primary_key=True,
		nullable=False,
	)
	inn: Mapped[str] = mapped_column(String(12), nullable=False, unique=True)
	snils: Mapped[str] = mapped_column(String(11), nullable=False, unique=True)

__all__ = ["Identifier"]
