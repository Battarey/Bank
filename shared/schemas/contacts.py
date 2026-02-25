from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, constr

class ContactsPayload(BaseModel):
	email: EmailStr
	phone: constr(pattern=r"^\+\d{10,15}$")

	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class ContactsResponse(ContactsPayload):
	client_id: UUID

	model_config = ConfigDict(from_attributes=True)


class ContactsUpdate(BaseModel):
	"""Частичное обновление контактов — email и/или phone."""
	email: EmailStr | None = None
	phone: constr(pattern=r"^\+\d{10,15}$") | None = None

	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


__all__ = ["ContactsPayload", "ContactsResponse", "ContactsUpdate"]
