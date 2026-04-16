"""Схемы разблокировки аккаунта."""

from .auth import Phone, Pin

Code = Annotated[str, Field(pattern=r"^\d{6}$", description="6-значный код разблокировки")]


class RequestUnlockRequest(BaseModel):
	"""Запрос на отправку кода восстановления доступа."""

	phone: Phone


class UnlockRequest(BaseModel):
	"""Запрос на восстановление доступа с обновлением PIN клиента."""

	phone: Phone
	code: Code
	new_pin: Pin = Field(description="Новый PIN-код для доступа к аккаунту")
