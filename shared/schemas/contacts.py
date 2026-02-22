from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, constr

class ContactsPayload(BaseModel):
	email: EmailStr
	phone: constr(pattern=r"^\+\d{10,15}$")

	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class ContactsResponse(ContactsPayload):
	client_id: UUID

	model_config = ConfigDict(from_attributes=True)

__all__ = ["ContactsPayload", "ContactsResponse"]
