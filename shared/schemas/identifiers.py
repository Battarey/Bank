from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, constr

class IdentifiersPayload(BaseModel):
	"""Идентификаторы налогоплательщика и социального страхования."""

	inn: constr(pattern=r"^\d{12}$") = Field(description="ИНН (12 цифр)")
	snils: constr(pattern=r"^\d{11}$") = Field(description="СНИЛС (11 цифр, без дефисов)")

	model_config = ConfigDict(extra="forbid")

class IdentifiersResponse(IdentifiersPayload):
	"""Идентификаторы клиента (ответ)."""

	client_id: UUID = Field(description="UUID клиента")

	model_config = ConfigDict(from_attributes=True)

__all__ = ["IdentifiersPayload", "IdentifiersResponse"]
