from datetime import date
from uuid import UUID
from pydantic import BaseModel, ConfigDict, constr, model_validator

class PassportPayload(BaseModel):
	series: constr(pattern=r"^\d{4}$")
	number: constr(pattern=r"^\d{6}$")
	division_code: constr(pattern=r"^\d{3}-\d{3}$")
	issued_by: constr(min_length=3, max_length=255)
	issued_at: date
	expiration_date: date
	registration_address: constr(min_length=3, max_length=255)

	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

	@model_validator(mode="after")
	def validate_dates(self) -> "PassportPayload":
		if self.expiration_date <= self.issued_at:
			raise ValueError("expiration_date must be later than issued_at")
		return self

class PassportResponse(PassportPayload):
	client_id: UUID

	model_config = ConfigDict(from_attributes=True)

__all__ = ["PassportPayload", "PassportResponse"]
