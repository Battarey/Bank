"""Роутер онбординга: создание черновиков и финализация профиля пользователя."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared import schemas
from shared.database_core.db import get_session
from . import service

router = APIRouter(
	prefix="/onboarding",
	tags=["onboarding"],
)


@router.post(
	"",
	response_model=schemas.StartOnboardingResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Начать процесс регистрации",
)
async def start_onboarding(session: AsyncSession = Depends(get_session)):
	"""Создаёт временного пользователя и возвращает UUID для прохождения шагов."""
	user_id = await service.start_onboarding(session)
	return schemas.StartOnboardingResponse(client_id=user_id)


@router.post(
	"/{user_id}/personal-data",
	response_model=schemas.PersonalDataResponse,
	summary="Шаг 1: Персональные данные",
)
async def store_personal_data(
	user_id: UUID,
	payload: schemas.PersonalDataPayload,
	session: AsyncSession = Depends(get_session),
):
	"""Сохраняет ФИО и дату рождения в черновик."""
	return await service.store_personal_data(session, user_id, payload)


@router.post(
	"/{user_id}/passport",
	response_model=schemas.PassportResponse,
	summary="Шаг 2: Паспортные данные",
)
async def store_passport_data(
	user_id: UUID,
	payload: schemas.PassportPayload,
	session: AsyncSession = Depends(get_session),
):
	"""Сохраняет данные паспорта с проверкой уникальности."""
	return await service.store_passport_data(session, user_id, payload)


@router.post(
	"/{user_id}/identifiers",
	response_model=schemas.IdentifiersResponse,
	summary="Шаг 3: ИНН и СНИЛС",
)
async def store_identifiers(
	user_id: UUID,
	payload: schemas.IdentifiersPayload,
	session: AsyncSession = Depends(get_session),
):
	"""Сохраняет ИНН и СНИЛС в черновик."""
	return await service.store_identifiers(session, user_id, payload)


@router.post(
	"/{user_id}/contacts",
	response_model=schemas.ContactsResponse,
	summary="Шаг 4: Контактные данные",
)
async def store_contacts(
	user_id: UUID,
	payload: schemas.ContactsPayload,
	session: AsyncSession = Depends(get_session),
):
	"""Сохраняет Email и телефон. Требуется последующая верификация Email."""
	return await service.store_contacts(session, user_id, payload)


@router.post(
	"/{user_id}/activation",
	response_model=schemas.FinalizeResponse,
	summary="Завершить регистрацию",
)
async def finalize_onboarding(
	user_id: UUID,
	session: AsyncSession = Depends(get_session),
):
	"""Переносит данные из черновиков в БД и активирует пользователя.
	
	Требует, чтобы все 4 шага были заполнены и email был подтверждён.
	"""
	await service.persist_onboarding_data(session, user_id)
	return schemas.FinalizeResponse(
		client_id=user_id,
		message="Регистрация успешно завершена. Теперь вы можете войти в систему.",
	)
