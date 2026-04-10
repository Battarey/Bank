"""Схемы разблокировки аккаунта."""

from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

Code = Annotated[str, Field(pattern=r"^\d{6}$", description="6-значный код разблокировки")]


class RequestUnlockRequest(BaseModel):
	"""Запрос на отправку кода разблокировки."""

	email: EmailStr


class UnlockRequest(BaseModel):
	"""Запрос на разблокировку аккаунта."""

	email: EmailStr
	code: Code
