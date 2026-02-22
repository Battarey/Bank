from uuid import UUID
from pydantic import BaseModel, ConfigDict, constr

class IdentifiersPayload(BaseModel):
	inn: constr(pattern=r"^\d{12}$")
	snils: constr(pattern=r"^\d{11}$")

	model_config = ConfigDict(extra="forbid")

class IdentifiersResponse(IdentifiersPayload):
	client_id: UUID

	model_config = ConfigDict(from_attributes=True)

__all__ = ["IdentifiersPayload", "IdentifiersResponse"]
