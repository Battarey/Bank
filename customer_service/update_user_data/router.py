"""Роутер обновления данных пользователя."""

from typing import Awaitable, Callable, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared import schemas
from shared.database_core.db import get_session
from shared.internal_auth import require_user_id
from . import service

router = APIRouter(
	prefix="/users",
	tags=["user-update"],
)


T = TypeVar("T")


async def _run(
	step: Callable[[], Awaitable[T]],
	session: AsyncSession,
) -> T:
	"""Обёртка для обработки сервисных исключений."""
	try:
		return await step()
	except service.UpdateDataNotFound as exc:
		raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
	except service.UpdateDataConflict as exc:
		await session.rollback()
		raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
	except service.UpdateDataEmpty as exc:
		raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
	except service.UpdateDataError as exc:
		raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch(
	"/personal-data",
	response_model=schemas.PersonalDataResponse,
	status_code=status.HTTP_200_OK,
	summary="Обновить персональные данные",
)
async def update_personal_data(
	payload: schemas.PersonalDataUpdate,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Обновляет ФИО пользователя. Дата рождения и пол неизменяемы."""
	return await _run(
		lambda: service.update_personal_data(session, user_id, payload),
		session,
	)


@router.put(
	"/passport",
	response_model=schemas.PassportResponse,
	status_code=status.HTTP_200_OK,
	summary="Заменить паспортные данные",
)
async def replace_passport(
	payload: schemas.PassportPayload,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Полная замена паспортных данных (все поля обязательны)."""
	return await _run(
		lambda: service.replace_passport(session, user_id, payload),
		session,
	)


@router.patch(
	"/contacts",
	response_model=schemas.ContactsResponse,
	status_code=status.HTTP_200_OK,
	summary="Обновить контакты",
)
async def update_contacts(
	payload: schemas.ContactsUpdate,
	user_id: UUID = Depends(require_user_id),
	session: AsyncSession = Depends(get_session),
):
	"""Частичное обновление email и/или телефона."""
	return await _run(
		lambda: service.update_contacts(session, user_id, payload),
		session,
	)
