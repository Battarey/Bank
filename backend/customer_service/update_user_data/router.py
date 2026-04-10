"""Роутер обновления профиля активного пользователя."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared import schemas
from shared.internal_auth import require_user_id

from ..uow import CustomerUnitOfWork, get_uow
from . import service

router = APIRouter(
	prefix="/users",
	tags=["user-update"],
)


@router.get(
	"/me",
	response_model=schemas.FullProfileResponse,
	status_code=status.HTTP_200_OK,
	summary="Получить полный агрегированный профиль",
)
async def get_my_profile(
	user_id: UUID = Depends(require_user_id),
	uow: CustomerUnitOfWork = Depends(get_uow),
):
	"""Возвращает все данные профиля пользователя (ФИО, паспорт, контакты, ИНН/СНИЛС) в одном ответе."""
	return await service.get_full_profile(uow, user_id)


@router.patch(
	"/personal-data",
	response_model=schemas.PersonalDataResponse,
	status_code=status.HTTP_200_OK,
	summary="Обновить ФИО",
)
async def update_personal_data(
	payload: schemas.PersonalDataUpdate,
	user_id: UUID = Depends(require_user_id),
	uow: CustomerUnitOfWork = Depends(get_uow),
):
	"""Частичное обновление ФИО пользователя. Дата рождения и пол неизменяемы."""
	return await service.update_personal_data(uow, user_id, payload)


@router.put(
	"/passport",
	response_model=schemas.PassportResponse,
	status_code=status.HTTP_200_OK,
	summary="Заменить паспорт",
)
async def replace_passport(
	payload: schemas.PassportPayload,
	user_id: UUID = Depends(require_user_id),
	uow: CustomerUnitOfWork = Depends(get_uow),
):
	"""Полная замена паспортных данных (например, при получении нового документа)."""
	return await service.replace_passport(uow, user_id, payload)


@router.patch(
	"/contacts",
	response_model=schemas.ContactsResponse,
	status_code=status.HTTP_200_OK,
	summary="Обновить Email/Телефон",
)
async def update_contacts(
	payload: schemas.ContactsUpdate,
	user_id: UUID = Depends(require_user_id),
	uow: CustomerUnitOfWork = Depends(get_uow),
):
	"""Частичное обновление контактных данных пользователя."""
	return await service.update_contacts(uow, user_id, payload)
