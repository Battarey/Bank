"""Роутер онбординга: создание черновиков и финализация профиля пользователя."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared import schemas

from ..core.uow import CustomerUnitOfWork, get_uow
from ..services import onboarding as service

router = APIRouter(
	prefix="/onboarding",
	tags=["onboarding"],
)


@router.post(
	"",
	response_model=schemas.StartInternalResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Начать процесс регистрации",
)
async def start_onboarding(uow: CustomerUnitOfWork = Depends(get_uow)):
	"""Создаёт временного пользователя и возвращает UUID для прохождения шагов."""
	user_id = await service.start_onboarding(uow)
	return schemas.StartInternalResponse(user_id=user_id, status="pending")


@router.post(
	"/{user_id}/personal-data",
	response_model=schemas.PersonalDataResponse,
	summary="Шаг 1: Персональные данные",
)
async def store_personal_data(
	user_id: UUID,
	payload: schemas.PersonalDataPayload,
	uow: CustomerUnitOfWork = Depends(get_uow),
):
	"""Сохраняет ФИО и дату рождения в черновик."""
	return await service.store_personal_data(uow, user_id, payload)


@router.post(
	"/{user_id}/passport",
	response_model=schemas.PassportResponse,
	summary="Шаг 2: Паспортные данные",
)
async def store_passport_data(
	user_id: UUID,
	payload: schemas.PassportPayload,
	uow: CustomerUnitOfWork = Depends(get_uow),
):
	"""Сохраняет данные паспорта с проверкой уникальности."""
	return await service.store_passport_data(uow, user_id, payload)


@router.post(
	"/{user_id}/identifiers",
	response_model=schemas.IdentifiersResponse,
	summary="Шаг 3: ИНН и СНИЛС",
)
async def store_identifiers(
	user_id: UUID,
	payload: schemas.IdentifiersPayload,
	uow: CustomerUnitOfWork = Depends(get_uow),
):
	"""Сохраняет ИНН и СНИЛС в черновик."""
	return await service.store_identifiers(uow, user_id, payload)


@router.post(
	"/{user_id}/contacts",
	response_model=schemas.ContactsResponse,
	summary="Шаг 4: Контактные данные",
)
async def store_contacts(
	user_id: UUID,
	payload: schemas.ContactsPayload,
	uow: CustomerUnitOfWork = Depends(get_uow),
):
	"""Сохраняет Email и телефон. Требуется последующая верификация Email."""
	return await service.store_contacts(uow, user_id, payload)


@router.post(
	"/{user_id}/email/send",
	status_code=status.HTTP_200_OK,
	summary="Отправить код подтверждения на Email",
)
async def send_verification_email(
	user_id: UUID,
	uow: CustomerUnitOfWork = Depends(get_uow),
):
	"""Генерирует код и отправляет его на указанный в черновике Email."""
	await service.send_verification_email(uow, user_id)
	return {"message": "Код подтверждения отправлен на вашу почту."}


@router.post(
	"/{user_id}/email/verify",
	status_code=status.HTTP_200_OK,
	summary="Подтвердить Email кодом",
)
async def verify_email(
	user_id: UUID,
	payload: schemas.EmailVerifyPayload,
):
	"""Проверяет код. Если код верный, Email помечается как подтверждённый."""
	success = await service.verify_email(user_id, payload.code)
	if not success:
		from ..core.exceptions import OnboardingError

		raise OnboardingError("Неверный код или срок его действия истёк.")
	return {"message": "Email успешно подтверждён."}


@router.post(
	"/{user_id}/completion",
	response_model=schemas.FinalizeInternalResponse,
	summary="Завершить регистрацию и создать профиль",
)
async def complete_onboarding(
	user_id: UUID,
	uow: CustomerUnitOfWork = Depends(get_uow),
):
	"""Переносит данные из черновиков в основной профиль и активирует пользователя."""
	await service.persist_onboarding_data(uow, user_id)
	return schemas.FinalizeInternalResponse(
		status="completed",
		message="Регистрация успешно завершена. Теперь вы можете войти в систему.",
	)
