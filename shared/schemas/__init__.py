"""Pydantic-схемы, доступные для всех микросервисов."""

from .auth import (
	LoginPinRequest,
	LoginPinResponse,
	MessageResponse,
	SetPinRequest,
)
from .contacts import ContactsPayload, ContactsResponse, ContactsUpdate
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
	"SetPinRequest",
	"StartInternalResponse",
	"StartOnboardingResponse",
]
