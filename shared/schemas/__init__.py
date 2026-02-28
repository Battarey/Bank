"""Pydantic-схемы, доступные для всех микросервисов."""

from .auth import (
	LoginPinRequest,
	LoginPinResponse,
	MessageResponse,
	SetPinRequest,
)
from .contacts import ContactsPayload, ContactsResponse, ContactsUpdate
from .email_verification import EmailCodeResponse, SendEmailCodeRequest, VerifyEmailCodeRequest
from .identifiers import IdentifiersPayload, IdentifiersResponse
from .onboarding import (
	FinalizeInternalResponse,
	FinalizeResponse,
	StartInternalResponse,
	StartOnboardingResponse,
)
from .passport import PassportPayload, PassportResponse
from .personal_data import PersonalDataPayload, PersonalDataResponse, PersonalDataUpdate

__all__ = [
	"ContactsPayload",
	"ContactsResponse",
	"ContactsUpdate",
	"EmailCodeResponse",
	"FinalizeInternalResponse",
	"FinalizeResponse",
	"IdentifiersPayload",
	"IdentifiersResponse",
	"LoginPinRequest",
	"LoginPinResponse",
	"MessageResponse",
	"PassportPayload",
	"PassportResponse",
	"PersonalDataPayload",
	"PersonalDataResponse",
	"PersonalDataUpdate",
	"SendEmailCodeRequest",
	"SetPinRequest",
	"StartInternalResponse",
	"StartOnboardingResponse",
	"VerifyEmailCodeRequest",
]
