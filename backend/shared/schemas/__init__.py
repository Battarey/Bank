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
from .contacts import ContactsPayload, ContactsResponse, ContactsUpdate, EmailVerifyPayload
from .currency import (
	ExchangeRatePairResponse,
	ExchangeRatesResponse,
	ExchangeRequest,
	ExchangeResponse,
)
from .customer import FullProfileResponse
from .email_verification import EmailCodeResponse, SendEmailCodeRequest, VerifyEmailCodeRequest
from .identifiers import IdentifiersPayload, IdentifiersResponse
from .metal import (
	MetalRateResponse,
	MetalRatesListResponse,
)
from .notification import NotificationPayload, NotificationTask
from .onboarding import (
	FinalizeInternalResponse,
	FinalizeResponse,
	StartInternalResponse,
	StartOnboardingResponse,
)
from .passport import PassportPayload, PassportResponse
from .personal_data import PersonalDataPayload, PersonalDataResponse, PersonalDataUpdate
from .security import (
	SecurityCheckRequest,
	SecurityCheckResponse,
	ViolationItem,
)
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
	"EmailVerifyPayload",
	"ExchangeRatePairResponse",
	"ExchangeRatesResponse",
	"ExchangeRequest",
	"ExchangeResponse",
	"FinalizeInternalResponse",
	"FinalizeResponse",
	"FullProfileResponse",
	"IdentifiersPayload",
	"IdentifiersResponse",
	"LoginPinRequest",
	"LoginPinResponse",
	"MessageResponse",
	"MetalRateResponse",
	"MetalRatesListResponse",
	"NotificationPayload",
	"NotificationTask",
	"OpenAccountRequest",
	"PassportPayload",
	"PassportResponse",
	"PersonalDataPayload",
	"PersonalDataResponse",
	"PersonalDataUpdate",
	"RequestUnlockRequest",
	"SecurityCheckRequest",
	"SecurityCheckResponse",
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
	"ViolationItem",
	"WithdrawalRequest",
]
