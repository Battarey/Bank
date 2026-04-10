"""ORM-модель паспортных данных."""

from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .types import EncryptedString


class Passport(Base):
	"""Паспортные данные клиента."""

	__tablename__ = "passport"

	client_id: Mapped[UUID] = mapped_column(
		PGUUID(as_uuid=True),
		ForeignKey("users.id", ondelete="CASCADE"),
		primary_key=True,
		nullable=False,
	)
	# Шифрованные данные (недетерминированные)
	series: Mapped[str] = mapped_column(EncryptedString, nullable=False)
	number: Mapped[str] = mapped_column(EncryptedString, nullable=False)
	division_code: Mapped[str] = mapped_column(EncryptedString, nullable=False)
	issued_by: Mapped[str] = mapped_column(EncryptedString, nullable=False)
	registration_address: Mapped[str] = mapped_column(EncryptedString, nullable=False)

	# Слепой индекс (детерминированный хеш) для обеспечения уникальности серии+номера.
	# Позволяет проверять уникальность без расшифровки всех записей.
	passport_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

	issued_at: Mapped[date] = mapped_column(Date, nullable=False)
	expiration_date: Mapped[date] = mapped_column(Date, nullable=False)

	__table_args__ = (
		# Индекс passport_hash уже уникален, UniqueConstraint на series/number не сработает
		# из-за шифрования, поэтому мы его убираем из БД, заменяя на passport_hash.
	)


__all__ = ["Passport"]
