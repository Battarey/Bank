"""Маршруты customer_service — онбординг, управление пользователями."""

import secrets
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from shared import schemas
from shared.redis_onboarding.tokens import (
	delete_onboarding_token,
	generate_token as generate_onboarding_token,
	load_onboarding_token,
	save_onboarding_token,
	touch_onboarding_token,
)
from shared.redis_sessions.tokens import save_token as save_session_token
from ..helpers import forward_request
from ..middleware import onboarding_token_scheme, session_token_scheme

onboarding_router = APIRouter(tags=["onboarding"])
onboarding_steps_router = APIRouter(
	tags=["onboarding"],
	dependencies=[Depends(onboarding_token_scheme)],
)
update_router = APIRouter(
	tags=["user-update"],
	dependencies=[Depends(session_token_scheme)],
)


# ── Зависимость: onboarding-токен → user_id ────────────────────────────


async def _resolve_onboarding(
	token: str | None = Depends(onboarding_token_scheme),
) -> UUID:
	"""Извлекает и проверяет X-Onboarding-Token, возвращает user_id."""

	if not token:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Заголовок X-Onboarding-Token обязателен.",
		)
	user_id = await load_onboarding_token(token)
	if user_id is None:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Onboarding-токен невалиден или истёк.",
		)

	# Скользящая экспирация: продлеваем TTL при каждом шаге
	await touch_onboarding_token(token)

	return user_id


# ── Онбординг ──────────────────────────────────────────────────────────


@onboarding_router.post(
	"/users/start",
	response_model=schemas.StartOnboardingResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Начать регистрацию",
)
async def start_onboarding(request: Request):
	"""Создаёт нового пользователя и возвращает `onboarding_token` для прохождения шагов регистрации."""
	data = await forward_request(
		request,
		"POST",
		"/users/start",
	)

	user_id = UUID(data["user_id"])
	token = generate_onboarding_token()
	await save_onboarding_token(token, user_id)

	return schemas.StartOnboardingResponse(
		onboarding_token=token,
		status=data["status"],
	)


@onboarding_steps_router.post(
	"/users/me/account/personal-data",
	response_model=schemas.PersonalDataResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Шаг 1: Персональные данные",
)
async def submit_personal_data(
	payload: schemas.PersonalDataPayload,
	request: Request,
	user_id: UUID = Depends(_resolve_onboarding),
):
	"""Сохраняет ФИО, дату рождения и пол клиента."""
	data = await forward_request(
		request,
		"POST",
		f"/users/{user_id}/account/personal-data",
		payload.model_dump(mode="json"),
	)
	return schemas.PersonalDataResponse.model_validate(data)


@onboarding_steps_router.post(
	"/users/me/account/passport",
	response_model=schemas.PassportResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Шаг 2: Паспортные данные",
)
async def submit_passport_data(
	payload: schemas.PassportPayload,
	request: Request,
	user_id: UUID = Depends(_resolve_onboarding),
):
	"""Сохраняет серию, номер, кем выдан и прочие паспортные сведения."""
	data = await forward_request(
		request,
		"POST",
		f"/users/{user_id}/account/passport",
		payload.model_dump(mode="json"),
	)
	return schemas.PassportResponse.model_validate(data)


@onboarding_steps_router.post(
	"/users/me/account/identifiers",
	response_model=schemas.IdentifiersResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Шаг 3: ИНН и СНИЛС",
)
async def submit_identifiers(
	payload: schemas.IdentifiersPayload,
	request: Request,
	user_id: UUID = Depends(_resolve_onboarding),
):
	"""Сохраняет идентификаторы налогоплательщика и социального страхования."""
	data = await forward_request(
		request,
		"POST",
		f"/users/{user_id}/account/identifiers",
		payload.model_dump(mode="json"),
	)
	return schemas.IdentifiersResponse.model_validate(data)


@onboarding_steps_router.post(
	"/users/me/account/contacts",
	response_model=schemas.ContactsResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Шаг 4: Контактные данные",
)
async def submit_contacts(
	payload: schemas.ContactsPayload,
	request: Request,
	user_id: UUID = Depends(_resolve_onboarding),
):
	"""Сохраняет email и номер телефона клиента."""
	data = await forward_request(
		request,
		"POST",
		f"/users/{user_id}/account/contacts",
		payload.model_dump(mode="json"),
	)
	return schemas.ContactsResponse.model_validate(data)


@onboarding_steps_router.post(
	"/users/me/account/send-email-code",
	response_model=schemas.EmailCodeResponse,
	status_code=status.HTTP_200_OK,
	summary="Отправить код на email",
)
async def send_email_code(
	request: Request,
	user_id: UUID = Depends(_resolve_onboarding),
):
	"""Отправляет 6-значный код подтверждения на email из шага 4 (contacts)."""
	data = await forward_request(
		request,
		"POST",
		f"/users/{user_id}/account/send-email-code",
	)
	return schemas.EmailCodeResponse.model_validate(data)


@onboarding_steps_router.post(
	"/users/me/account/verify-email",
	response_model=schemas.EmailCodeResponse,
	status_code=status.HTTP_200_OK,
	summary="Подтвердить email",
)
async def verify_email(
	payload: schemas.VerifyEmailCodeRequest,
	request: Request,
	user_id: UUID = Depends(_resolve_onboarding),
):
	"""Проверяет 6-значный код. После успешной верификации можно вызывать finalize."""
	data = await forward_request(
		request,
		"POST",
		f"/users/{user_id}/account/verify-email",
		payload.model_dump(mode="json"),
	)
	return schemas.EmailCodeResponse.model_validate(data)


@onboarding_steps_router.post(
	"/users/me/account/finalize",
	response_model=schemas.FinalizeResponse,
	status_code=status.HTTP_200_OK,
	summary="Завершить регистрацию",
)
async def finalize_onboarding(
	request: Request,
	user_id: UUID = Depends(_resolve_onboarding),
	onb_token: str | None = Depends(onboarding_token_scheme),
):
	"""Переносит данные из черновиков в БД, выдаёт сессионный токен и удаляет onboarding-токен."""
	data = await forward_request(
		request,
		"POST",
		f"/users/{user_id}/account/finalize",
	)

	# Удаляем onboarding-токен — он больше не нужен
	if onb_token:
		await delete_onboarding_token(onb_token)

	# Автовыдача сессионного токена
	session_token = secrets.token_urlsafe(32)
	await save_session_token(session_token, user_id)

	return schemas.FinalizeResponse(
		status=data["status"],
		message=data["message"],
		session_token=session_token,
		user_id=user_id,
	)


# ── Обновление данных пользователя ─────────────────────────────────────


@update_router.patch(
	"/users/me/personal-data",
	response_model=schemas.PersonalDataResponse,
	status_code=status.HTTP_200_OK,
	summary="Обновить персональные данные",
)
async def update_personal_data(
	payload: schemas.PersonalDataUpdate,
	request: Request,
):
	"""Частичное обновление ФИО. Дата рождения и пол неизменяемы."""
	data = await forward_request(
		request,
		"PATCH",
		"/users/personal-data",
		payload.model_dump(mode="json", exclude_unset=True),
	)
	return schemas.PersonalDataResponse.model_validate(data)


@update_router.put(
	"/users/me/passport",
	response_model=schemas.PassportResponse,
	status_code=status.HTTP_200_OK,
	summary="Заменить паспортные данные",
)
async def replace_passport(
	payload: schemas.PassportPayload,
	request: Request,
):
	"""Полная замена паспортных данных (все поля обязательны)."""
	data = await forward_request(
		request,
		"PUT",
		"/users/passport",
		payload.model_dump(mode="json"),
	)
	return schemas.PassportResponse.model_validate(data)


@update_router.patch(
	"/users/me/contacts",
	response_model=schemas.ContactsResponse,
	status_code=status.HTTP_200_OK,
	summary="Обновить контактные данные",
)
async def update_contacts(
	payload: schemas.ContactsUpdate,
	request: Request,
):
	"""Частичное обновление email и/или телефона."""
	data = await forward_request(
		request,
		"PATCH",
		"/users/contacts",
		payload.model_dump(mode="json", exclude_unset=True),
	)
	return schemas.ContactsResponse.model_validate(data)
