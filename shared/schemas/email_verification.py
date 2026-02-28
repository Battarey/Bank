"""Pydantic-схемы для верификации email."""

from pydantic import BaseModel, EmailStr, Field


class SendEmailCodeRequest(BaseModel):
	"""Запрос на отправку кода подтверждения email."""

	email: EmailStr = Field(description="Email-адрес, на который будет отправлен код")


class VerifyEmailCodeRequest(BaseModel):
	"""Запрос на проверку кода подтверждения email."""

	code: str = Field(
		pattern=r"^\d{6}$",
		description="6-значный код подтверждения из письма",
	)


class EmailCodeResponse(BaseModel):
	"""Ответ на отправку / проверку кода."""

	message: str = Field(description="Текст сообщения")
	email_verified: bool = Field(description="Подтверждён ли email")


__all__ = [
	"EmailCodeResponse",
	"SendEmailCodeRequest",
	"VerifyEmailCodeRequest",
]
