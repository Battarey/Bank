"""Pydantic-схемы для онбординга."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class StartInternalResponse(BaseModel):
	"""Внутренний ответ customer_service на начало онбординга."""

	user_id: UUID = Field(description="UUID созданного пользователя")
	status: Literal["pending"] = Field(description="Статус онбординга")


class StartOnboardingResponse(BaseModel):
	"""Ответ на начало регистрации — содержит onboarding-токен для прохождения шагов."""

	onboarding_token: str = Field(description="Токен для прохождения шагов регистрации (TTL 60 мин)")
	status: Literal["pending"] = Field(description="Статус онбординга")


class FinalizeInternalResponse(BaseModel):
	"""Внутренний ответ customer_service на завершение онбординга."""

	status: Literal["completed"] = Field(description="Статус онбординга")
	message: str = Field(description="Сообщение о результате")


class FinalizeResponse(FinalizeInternalResponse):
	"""Ответ на завершение регистрации — включает сессионный токен для дальнейшей работы."""

	session_token: str = Field(description="Сессионный токен (TTL 30 мин)")
	user_id: UUID = Field(description="UUID пользователя")
