"""Настройки Transaction Service."""

from pydantic import Field

from shared.config import BaseAppSettings


class TransactionSettings(BaseAppSettings):
	"""Настройки для управления финансовыми операциями."""

	# URL внешних микросервисов
	CURRENCY_SERVICE_URL: str = Field(
		"http://currency_service:8000", 
		alias="CURRENCY_SERVICE_URL"
	)
	SECURITY_SERVICE_URL: str = Field(
		"http://security_service:8000", 
		alias="SECURITY_SERVICE_URL"
	)
