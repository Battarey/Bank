"""Pydantic-схемы паспортных данных."""

from datetime import date
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, constr, model_validator

class PassportPayload(BaseModel):
	"""Паспортные данные клиента."""

	series: constr(pattern=r"^\d{4}$") = Field(description="Серия паспорта (4 цифры)")
	number: constr(pattern=r"^\d{6}$") = Field(description="Номер паспорта (6 цифр)")
	division_code: constr(pattern=r"^\d{3}-\d{3}$") = Field(description="Код подразделения (формат: 000-000)")
	issued_by: constr(min_length=3, max_length=255) = Field(description="Кем выдан")
	issued_at: date = Field(description="Дата выдачи (YYYY-MM-DD)")
	expiration_date: date = Field(description="Срок действия (YYYY-MM-DD), должен быть позже issued_at")
	registration_address: constr(min_length=3, max_length=255) = Field(description="Адрес регистрации")

	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

	@model_validator(mode="after")
	def validate_dates(self) -> "PassportPayload":
		if self.expiration_date <= self.issued_at:
			raise ValueError("expiration_date must be later than issued_at")
		return self

class PassportResponse(PassportPayload):
	"""Паспортные данные клиента (ответ)."""

	client_id: UUID = Field(description="UUID клиента")

	model_config = ConfigDict(from_attributes=True)

__all__ = ["PassportPayload", "PassportResponse"]
