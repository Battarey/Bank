"""Pydantic-схемы, доступные для всех микросервисов."""

from .contacts import ContactsPayload, ContactsResponse, ContactsUpdate
from .identifiers import IdentifiersPayload, IdentifiersResponse
from .onboarding import FinalizeResponse, StartOnboardingResponse
from .passport import PassportPayload, PassportResponse
from .personal_data import PersonalDataPayload, PersonalDataResponse, PersonalDataUpdate

__all__ = [
	"ContactsPayload",
	"ContactsResponse",
	"ContactsUpdate",
	"FinalizeResponse",
	"IdentifiersPayload",
	"IdentifiersResponse",
	"PassportPayload",
	"PassportResponse",
	"PersonalDataPayload",
	"PersonalDataResponse",
	"PersonalDataUpdate",
	"StartOnboardingResponse",
]
