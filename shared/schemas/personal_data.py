from datetime import date
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, constr, field_validator

NameStr = constr(strip_whitespace=True, min_length=1, max_length=100)

class PersonalDataPayload(BaseModel):
	last_name: NameStr
	first_name: NameStr
	middle_name: NameStr | None = Field(default=None)
	birth_date: date
	gender: Literal["M", "F"]

	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

	@field_validator("gender", mode="before")
	@classmethod
	def _normalize_gender(cls, value: str) -> str:
		"""Допускает только 'M' или 'F', регистр не важен."""
		if isinstance(value, str):
			normalized = value.strip().upper()
			if normalized in {"M", "F"}:
				return normalized
		raise ValueError("gender must be 'M' or 'F'")

class PersonalDataResponse(PersonalDataPayload):
	client_id: UUID

	model_config = ConfigDict(from_attributes=True)

__all__ = ["PersonalDataPayload", "PersonalDataResponse"]
