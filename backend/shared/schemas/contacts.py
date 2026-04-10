"""Pydantic-схемы контактных данных."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, constr


class ContactsPayload(BaseModel):
	"""Контактные данные клиента."""

	email: EmailStr = Field(description="Email-адрес")
	phone: constr(pattern=r"^\+7\d{10}$") = Field(description="Телефон в формате +7XXXXXXXXXX")

	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class ContactsResponse(ContactsPayload):
	"""Контактные данные клиента (ответ)."""

	client_id: UUID = Field(description="UUID клиента")

	model_config = ConfigDict(from_attributes=True)


class ContactsUpdate(BaseModel):
	"""Частичное обновление контактов — email и/или телефон."""

	email: EmailStr | None = Field(default=None, description="Новый email-адрес")
	phone: constr(pattern=r"^\+7\d{10}$") | None = Field(default=None, description="Новый телефон в формате +7XXXXXXXXXX")

	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EmailVerifyPayload(BaseModel):
	"""Payload для подтверждения email кодом."""

	code: constr(pattern=r"^\d{6}$") = Field(description="6-значный код из письма")

	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


__all__ = ["ContactsPayload", "ContactsResponse", "ContactsUpdate", "EmailVerifyPayload"]
