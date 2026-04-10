"""ORM-модель персональных данных (ФИО, дата рождения, пол)."""

from datetime import date
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .types import EncryptedString


class PersonalData(Base):
	"""Персональные данные клиента (ФИО, дата рождения, пол)."""

	__tablename__ = "personal_data"
	__table_args__ = (
		CheckConstraint("gender IN ('M','F')", name="ck_personal_data_gender"),
	)

	client_id: Mapped[UUID] = mapped_column(
		PGUUID(as_uuid=True),
		ForeignKey("users.id", ondelete="CASCADE"),
		primary_key=True,
		nullable=False,
	)
	# Шифрованные данные
	last_name: Mapped[str] = mapped_column(EncryptedString, nullable=False)
	first_name: Mapped[str] = mapped_column(EncryptedString, nullable=False)
	middle_name: Mapped[str | None] = mapped_column(EncryptedString)

	birth_date: Mapped[date] = mapped_column(Date, nullable=False)
	gender: Mapped[str] = mapped_column(String(1), nullable=False)

__all__ = ["PersonalData"]
