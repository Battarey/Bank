"""ORM-модель идентификаторов (ИНН, СНИЛС)."""

from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.types import EncryptedString

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
	# Шифрованные данные
	inn: Mapped[str] = mapped_column(EncryptedString, nullable=False)
	snils: Mapped[str] = mapped_column(EncryptedString, nullable=False)

	# Слепые индексы для поиска и уникальности (Blind Index)
	inn_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
	snils_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)


__all__ = ["Identifier"]
