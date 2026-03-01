"""Pydantic-схемы, доступные для всех микросервисов."""

from .auth import (
	LoginPinRequest,
	LoginPinResponse,
	MessageResponse,
	SetPinRequest,
)
from .bank_account import (
	AccountListResponse,
	AccountMessageResponse,
	AccountResponse,
	CloseAccountRequest,
	OpenAccountRequest,
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
from .unlock import RequestUnlockRequest, UnlockRequest

__all__ = [
	"AccountListResponse",
	"AccountMessageResponse",
	"AccountResponse",
	"CloseAccountRequest",
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
	"OpenAccountRequest",
	"PassportPayload",
	"PassportResponse",
	"PersonalDataPayload",
	"PersonalDataResponse",
	"PersonalDataUpdate",
	"RequestUnlockRequest",
	"SendEmailCodeRequest",
	"SetPinRequest",
	"StartInternalResponse",
	"StartOnboardingResponse",
	"UnlockRequest",
	"VerifyEmailCodeRequest",
]
