"""Pydantic-схемы для онбординга."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class StartOnboardingResponse(BaseModel):
	"""Ответ на начало онбординга."""
	user_id: UUID
	status: Literal["pending"]


class FinalizeResponse(BaseModel):
	"""Ответ на завершение онбординга."""
	status: Literal["completed"]
	message: str
