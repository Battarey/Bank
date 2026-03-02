"""Pydantic-схемы персональных данных."""

from datetime import date
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, constr, field_validator

NameStr = constr(strip_whitespace=True, min_length=1, max_length=100)

class PersonalDataPayload(BaseModel):
	"""Персональные данные клиента: ФИО, дата рождения, пол."""

	last_name: NameStr = Field(description="Фамилия")
	first_name: NameStr = Field(description="Имя")
	middle_name: NameStr | None = Field(default=None, description="Отчество (необязательно)")
	birth_date: date = Field(description="Дата рождения (YYYY-MM-DD)")
	gender: Literal["M", "F"] = Field(description="Пол: M — мужской, F — женский")

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
	"""Персональные данные клиента (ответ)."""

	client_id: UUID = Field(description="UUID клиента")

	model_config = ConfigDict(from_attributes=True)


class PersonalDataUpdate(BaseModel):
	"""Частичное обновление ФИО. Дата рождения и пол неизменяемы."""

	last_name: NameStr | None = Field(default=None, description="Фамилия")
	first_name: NameStr | None = Field(default=None, description="Имя")
	middle_name: NameStr | None = Field(default=None, description="Отчество")

	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


__all__ = ["PersonalDataPayload", "PersonalDataResponse", "PersonalDataUpdate"]
