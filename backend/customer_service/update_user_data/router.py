"""Роутер обновления профиля активного пользователя."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared import schemas
from shared.database_core.db import get_session
from shared.internal_auth import require_user_id
from . import service

router = APIRouter(
	prefix="/users",
	tags=["user-update"],
)


@router.patch(
	"/personal-data",
	response_model=schemas.PersonalDataResponse,
	status_code=status.HTTP_200_OK,
	summary="Обновить ФИО",
)
async def update_personal_data(
	payload: schemas.PersonalDataUpdate,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Частичное обновление ФИО пользователя. Дата рождения и пол неизменяемы."""
	return await service.update_personal_data(session, user_id, payload)


@router.put(
	"/passport",
	response_model=schemas.PassportResponse,
	status_code=status.HTTP_200_OK,
	summary="Заменить паспорт",
)
async def replace_passport(
	payload: schemas.PassportPayload,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Полная замена паспортных данных (например, при получении нового документа)."""
	return await service.replace_passport(session, user_id, payload)


@router.patch(
	"/contacts",
	response_model=schemas.ContactsResponse,
	status_code=status.HTTP_200_OK,
	summary="Обновить Email/Телефон",
)
async def update_contacts(
	payload: schemas.ContactsUpdate,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Частичное обновление контактных данных пользователя."""
	return await service.update_contacts(session, user_id, payload)
