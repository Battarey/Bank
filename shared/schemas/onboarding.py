"""Pydantic-схемы для онбординга."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class StartInternalResponse(BaseModel):
	"""Внутренний ответ customer_service (содержит user_id)."""
	user_id: UUID
	status: Literal["pending"]


class StartOnboardingResponse(BaseModel):
	"""Ответ gateway (содержит onboarding-токен)."""
	onboarding_token: str
	status: Literal["pending"]


class FinalizeInternalResponse(BaseModel):
	"""Внутренний ответ customer_service на завершение онбординга."""
	status: Literal["completed"]
	message: str


class FinalizeResponse(FinalizeInternalResponse):
	"""Ответ gateway на завершение онбординга (включает сессионный токен)."""
	session_token: str
	user_id: UUID
