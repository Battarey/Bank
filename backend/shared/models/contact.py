"""ORM-модель контактных данных (телефон, email)."""

from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .types import EncryptedString


class Contact(Base):
	"""Контактные данные клиента."""

	__tablename__ = "contacts"

	client_id: Mapped[UUID] = mapped_column(
		PGUUID(as_uuid=True),
		ForeignKey("users.id", ondelete="CASCADE"),
		primary_key=True,
		nullable=False,
	)
	# Шифрованные данные
	email: Mapped[str] = mapped_column(EncryptedString, nullable=False)
	phone: Mapped[str] = mapped_column(EncryptedString, nullable=False)

	# Слепые индексы для поиска и уникальности
	email_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
	phone_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)


__all__ = ["Contact"]
