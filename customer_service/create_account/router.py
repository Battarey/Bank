"""Роутер онбординга — пошаговая регистрация клиента."""

from typing import Awaitable, Callable, TypeVar
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from shared import models, schemas
from shared.database_core.db import get_session
from shared.rabbitmq import publish, NOTIFICATIONS_EXCHANGE, EMAIL_ROUTING_KEY
from shared.redis_onboarding.email_codes import (
	generate_code,
	is_email_verified,
	save_email_code,
	verify_email_code,
)
from shared.redis_onboarding import drafts as onboarding_drafts
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
	response_model=schemas.StartInternalResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Начать онбординг",
)
async def start_onboarding(session: AsyncSession = Depends(get_session)) -> schemas.StartInternalResponse:
	"""Создаёт нового пользователя для начала онбординга."""

	user_id = await service.start_onboarding(session)
	return schemas.StartInternalResponse(user_id=user_id, status="pending")


@router.post(
	"/finalize",
	response_model=schemas.FinalizeInternalResponse,
	status_code=status.HTTP_200_OK,
	summary="Завершить онбординг",
)
async def finalize_onboarding(
	user_id: UUID,
	session: AsyncSession = Depends(get_session),
):
	"""Переносит данные из Redis в PostgreSQL и завершает онбординг."""

	await _run_step(lambda: service.persist_onboarding_data(session, user_id), session)

	# Отправляем приветственное письмо
	contact = await session.get(models.Contact, user_id)
	if contact:
		await publish(
			exchange_name=NOTIFICATIONS_EXCHANGE,
			routing_key=EMAIL_ROUTING_KEY,
			body={
				"type": "welcome",
				"payload": {
					"to": contact.email,
					"variables": {},
				},
			},
		)

	return schemas.FinalizeInternalResponse(status="completed", message="Пользователь успешно авторизован.")


@router.post(
	"/personal-data",
	response_model=schemas.PersonalDataResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Шаг 1: Персональные данные",
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
	summary="Шаг 2: Паспортные данные",
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
	summary="Шаг 3: ИНН и СНИЛС",
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
	summary="Шаг 4: Контактные данные",
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


# ── Верификация email ──────────────────────────────────────────────────


@router.post(
	"/send-email-code",
	response_model=schemas.EmailCodeResponse,
	status_code=status.HTTP_200_OK,
	summary="Отправить код на email",
)
async def send_email_code(user_id: UUID):
	"""Отправляет 6-значный код на email, указанный в черновике шага контактов.

	Перед вызовом необходимо пройти шаг 4 (contacts).
	"""

	draft = await onboarding_drafts.load_draft(user_id, "contacts")
	if draft is None or not draft.get("payload"):
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Сначала заполните контактные данные (шаг 4).",
		)

	email = draft["payload"].get("email")
	if not email:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Email не найден в черновике контактов.",
		)

	code = generate_code()
	await save_email_code(user_id, code)

	await publish(
		NOTIFICATIONS_EXCHANGE,
		EMAIL_ROUTING_KEY,
		{
			"type": "verification_code",
			"payload": {"to": email, "variables": {"code": code}},
		},
	)

	return schemas.EmailCodeResponse(
		message=f"Код отправлен на {email}.",
		email_verified=False,
	)


@router.post(
	"/verify-email",
	response_model=schemas.EmailCodeResponse,
	status_code=status.HTTP_200_OK,
	summary="Подтвердить email",
)
async def verify_email(user_id: UUID, payload: schemas.VerifyEmailCodeRequest):
	"""Проверяет 6-значный код, отправленный на email.

	После успешной верификации можно вызывать `/finalize`.
	"""

	success = await verify_email_code(user_id, payload.code)
	if not success:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Код неверный или истёк. Запросите новый.",
		)

	return schemas.EmailCodeResponse(
		message="Email успешно подтверждён.",
		email_verified=True,
	)


__all__ = ["router", "start_router"]
