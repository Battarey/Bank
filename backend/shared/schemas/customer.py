"""Pydantic-схемы для агрегированных данных клиента."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FullProfileResponse(BaseModel):
	"""Агрегированная карточка клиента со всеми персональными данными."""

	id: UUID = Field(description="UUID пользователя")
	status: str = Field(description="Статус аккаунта (active, pending, deleted, frozen)")
	created_at: datetime = Field(description="Дата регистрации")
	
	last_name: str = Field(description="Фамилия")
	first_name: str = Field(description="Имя")
	middle_name: str | None = Field(default=None, description="Отчество")
	birth_date: date = Field(description="Дата рождения")
	gender: str = Field(description="Пол (M/F)")
	
	email: str = Field(description="Email (расшифрованный)")
	phone: str = Field(description="Телефон (расшифрованный)")
	
	passport_series: str = Field(description="Серия паспорта (расшифрованная)")
	passport_number: str = Field(description="Номер паспорта (расшифрованный)")
	
	inn: str = Field(description="ИНН (расшифрованный)")
	snils: str = Field(description="СНИЛС (расшифрованный)")
	
	model_config = ConfigDict(from_attributes=True)
