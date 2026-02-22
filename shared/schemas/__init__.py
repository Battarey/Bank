"""Pydantic-схемы, доступные для всех микросервисов."""

from .contacts import ContactsPayload, ContactsResponse
from .identifiers import IdentifiersPayload, IdentifiersResponse
from .onboarding import FinalizeResponse, StartOnboardingResponse
from .passport import PassportPayload, PassportResponse
from .personal_data import PersonalDataPayload, PersonalDataResponse

__all__ = [
	"ContactsPayload",
	"ContactsResponse",
	"FinalizeResponse",
	"IdentifiersPayload",
	"IdentifiersResponse",
	"PassportPayload",
	"PassportResponse",
	"PersonalDataPayload",
	"PersonalDataResponse",
	"StartOnboardingResponse",
]
