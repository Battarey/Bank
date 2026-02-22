from typing import Awaitable, Callable, TypeVar
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from shared import schemas
from shared.database_core.db import get_session
from . import service

router = APIRouter(
	prefix="/users/{user_id}/account",
	tags=["user-account"],
)

start_router = APIRouter(
	prefix="/users",
	tags=["user-account"],
)


T = TypeVar("T")


async def _run_step(
	step: Callable[[], Awaitable[T]],
	session: AsyncSession,
) -> T:
	try:
		return await step()
	except service.AccountDataConflict as exc:  # pragma: no cover - обработка FastAPI
		await session.rollback()
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail=str(exc),
		) from exc
	except service.AccountDataError as exc:  # pragma: no cover - обработка FastAPI
		await session.rollback()
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=str(exc),
		) from exc


@start_router.post(
	"/start",
	response_model=schemas.StartOnboardingResponse,
	status_code=status.HTTP_201_CREATED,
)
async def start_onboarding(session: AsyncSession = Depends(get_session)) -> schemas.StartOnboardingResponse:
	"""Создаёт нового пользователя для начала онбординга."""

	user_id = await service.start_onboarding(session)
	return schemas.StartOnboardingResponse(user_id=user_id, status="pending")


@router.post(
	"/finalize",
	response_model=schemas.FinalizeResponse,
	status_code=status.HTTP_200_OK,
)
async def finalize_onboarding(
	user_id: UUID,
	session: AsyncSession = Depends(get_session),
):
	"""Переносит данные из Redis в PostgreSQL и завершает онбординг."""

	await _run_step(lambda: service.persist_onboarding_data(session, user_id), session)
	return schemas.FinalizeResponse(status="completed", message="Пользователь успешно авторизован.")


@router.post(
	"/personal-data",
	response_model=schemas.PersonalDataResponse,
	status_code=status.HTTP_201_CREATED,
)
async def submit_personal_data(
	user_id: UUID,
	payload: schemas.PersonalDataPayload,
	session: AsyncSession = Depends(get_session),
):
	"""Сохраняет персональные данные (ФИО, дата рождения, пол)."""

	return await _run_step(
		lambda: service.store_personal_data(session, user_id, payload),
		session,
	)


@router.post(
	"/passport",
	response_model=schemas.PassportResponse,
	status_code=status.HTTP_201_CREATED,
)
async def submit_passport_data(
	user_id: UUID,
	payload: schemas.PassportPayload,
	session: AsyncSession = Depends(get_session),
):
	"""Сохраняет паспортные сведения, необходимые для KYC."""

	return await _run_step(
		lambda: service.store_passport_data(session, user_id, payload),
		session,
	)


@router.post(
	"/identifiers",
	response_model=schemas.IdentifiersResponse,
	status_code=status.HTTP_201_CREATED,
)
async def submit_identifiers(
	user_id: UUID,
	payload: schemas.IdentifiersPayload,
	session: AsyncSession = Depends(get_session),
):
	"""Сохраняет ИНН и СНИЛС пользователя."""

	return await _run_step(
		lambda: service.store_identifiers(session, user_id, payload),
		session,
	)


@router.post(
	"/contacts",
	response_model=schemas.ContactsResponse,
	status_code=status.HTTP_201_CREATED,
)
async def submit_contacts(
	user_id: UUID,
	payload: schemas.ContactsPayload,
	session: AsyncSession = Depends(get_session),
):
	"""Сохраняет email и телефон, которые будут использоваться для уведомлений."""

	return await _run_step(
		lambda: service.store_contacts(session, user_id, payload),
		session,
	)


__all__ = ["router", "start_router"]
