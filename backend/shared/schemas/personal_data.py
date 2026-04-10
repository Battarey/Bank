"""Pydantic-схемы персональных данных."""

import calendar
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, constr, field_validator

# Минимальный возраст для обслуживания в банке (лет)
MIN_AGE = 14
# Максимально допустимый возраст (лет)
MAX_AGE = 120

NameStr = constr(strip_whitespace=True, min_length=1, max_length=100)


class PersonalDataPayload(BaseModel):
	"""Персональные данные клиента: ФИО, дата рождения, пол."""

	last_name: NameStr = Field(description="Фамилия")
	first_name: NameStr = Field(description="Имя")
	middle_name: NameStr | None = Field(default=None, description="Отчество (необязательно)")
	birth_date: date = Field(description="Дата рождения (YYYY-MM-DD)")
	gender: Literal["M", "F"] = Field(description="Пол: M — мужской, F — женский")

	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

	@field_validator("birth_date")
	@classmethod
	def _validate_birth_date(cls, value: date) -> date:
		"""Проверяет корректность даты рождения.

		— Дата не в будущем.
		— Високосный год: 29 февраля допускается только для високосных годов.
		— Клиент не младше MIN_AGE лет (банковское обслуживание).
		— Клиент не старше MAX_AGE лет (невозможная дата рождения).
		"""
		today = date.today()

		# Проверка високосного года (29 февраля)
		if value.month == 2 and value.day == 29:
			if not calendar.isleap(value.year):
				raise ValueError(f"{value.year} не является високосным годом, дата 29 февраля невозможна")

		# Дата рождения не может быть в будущем
		if value > today:
			raise ValueError("Дата рождения не может быть в будущем")

		# Вычисление полного возраста
		age = today.year - value.year
		if (today.month, today.day) < (value.month, value.day):
			age -= 1

		if age < MIN_AGE:
			raise ValueError(f"Клиент должен быть не младше {MIN_AGE} лет (указан возраст: {age})")

		if age > MAX_AGE:
			raise ValueError(
				f"Дата рождения указывает на возраст {age} лет, что превышает максимально допустимый ({MAX_AGE})"
			)

		return value

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
