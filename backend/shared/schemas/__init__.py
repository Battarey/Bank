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
	OpenAccountRequest,
)
from .contacts import ContactsPayload, ContactsResponse, ContactsUpdate
from .currency import (
	ExchangeRatePairResponse,
	ExchangeRatesResponse,
	ExchangeRequest,
	ExchangeResponse,
)
from .email_verification import EmailCodeResponse, SendEmailCodeRequest, VerifyEmailCodeRequest
from .identifiers import IdentifiersPayload, IdentifiersResponse
from .metal import (
	MetalRateResponse,
	MetalRatesListResponse,
)
from .onboarding import (
	FinalizeInternalResponse,
	FinalizeResponse,
	StartInternalResponse,
	StartOnboardingResponse,
)
from .passport import PassportPayload, PassportResponse
from .personal_data import PersonalDataPayload, PersonalDataResponse, PersonalDataUpdate
from .transaction import (
	DepositRequest,
	TransactionCreateRequest,
	TransactionListResponse,
	TransactionMessageResponse,
	TransactionResponse,
	TransferRequest,
	WithdrawalRequest,
)
from .unlock import RequestUnlockRequest, UnlockRequest

__all__ = [
	"AccountListResponse",
	"AccountMessageResponse",
	"AccountResponse",
	"ContactsPayload",
	"ContactsResponse",
	"ContactsUpdate",
	"DepositRequest",
	"EmailCodeResponse",
	"ExchangeRatePairResponse",
	"ExchangeRatesResponse",
	"ExchangeRequest",
	"ExchangeResponse",
	"FinalizeInternalResponse",
	"FinalizeResponse",
	"IdentifiersPayload",
	"IdentifiersResponse",
	"LoginPinRequest",
	"LoginPinResponse",
	"MessageResponse",
	"MetalRateResponse",
	"MetalRatesListResponse",
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
	"TransactionCreateRequest",
	"TransactionListResponse",
	"TransactionMessageResponse",
	"TransactionResponse",
	"TransferRequest",
	"UnlockRequest",
	"VerifyEmailCodeRequest",
	"WithdrawalRequest",
]
