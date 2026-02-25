"""Маршруты customer_service — онбординг, управление пользователями."""

from uuid import UUID
from fastapi import APIRouter, Depends, Request, status
from shared import schemas
from ..helpers import forward_request
from ..middleware import session_token_scheme

onboarding_router = APIRouter(tags=["onboarding"])
update_router = APIRouter(
	tags=["user-update"],
	dependencies=[Depends(session_token_scheme)],
)


@onboarding_router.post(
	"/users/start",
	response_model=schemas.StartOnboardingResponse,
	status_code=status.HTTP_201_CREATED,
)
async def start_onboarding(request: Request):
	data = await forward_request(
		request,
		"POST",
		"/users/start",
	)
	return schemas.StartOnboardingResponse.model_validate(data)


@onboarding_router.post(
	"/users/{user_id}/account/personal-data",
	response_model=schemas.PersonalDataResponse,
	status_code=status.HTTP_201_CREATED,
)
async def submit_personal_data(
	user_id: UUID,
	payload: schemas.PersonalDataPayload,
	request: Request,
):
	data = await forward_request(
		request,
		"POST",
		f"/users/{user_id}/account/personal-data",
		payload.model_dump(mode="json"),
	)
	return schemas.PersonalDataResponse.model_validate(data)


@onboarding_router.post(
	"/users/{user_id}/account/passport",
	response_model=schemas.PassportResponse,
	status_code=status.HTTP_201_CREATED,
)
async def submit_passport_data(
	user_id: UUID,
	payload: schemas.PassportPayload,
	request: Request,
):
	data = await forward_request(
		request,
		"POST",
		f"/users/{user_id}/account/passport",
		payload.model_dump(mode="json"),
	)
	return schemas.PassportResponse.model_validate(data)


@onboarding_router.post(
	"/users/{user_id}/account/identifiers",
	response_model=schemas.IdentifiersResponse,
	status_code=status.HTTP_201_CREATED,
)
async def submit_identifiers(
	user_id: UUID,
	payload: schemas.IdentifiersPayload,
	request: Request,
):
	data = await forward_request(
		request,
		"POST",
		f"/users/{user_id}/account/identifiers",
		payload.model_dump(mode="json"),
	)
	return schemas.IdentifiersResponse.model_validate(data)


@onboarding_router.post(
	"/users/{user_id}/account/contacts",
	response_model=schemas.ContactsResponse,
	status_code=status.HTTP_201_CREATED,
)
async def submit_contacts(
	user_id: UUID,
	payload: schemas.ContactsPayload,
	request: Request,
):
	data = await forward_request(
		request,
		"POST",
		f"/users/{user_id}/account/contacts",
		payload.model_dump(mode="json"),
	)
	return schemas.ContactsResponse.model_validate(data)


@onboarding_router.post(
	"/users/{user_id}/account/finalize",
	response_model=schemas.FinalizeResponse,
	status_code=status.HTTP_200_OK,
)
async def finalize_onboarding(
	user_id: UUID,
	request: Request,
):
	data = await forward_request(
		request,
		"POST",
		f"/users/{user_id}/account/finalize",
	)
	return schemas.FinalizeResponse.model_validate(data)


# ── Обновление данных пользователя ─────────────────────────────────────


@update_router.patch(
	"/users/me/personal-data",
	response_model=schemas.PersonalDataResponse,
	status_code=status.HTTP_200_OK,
)
async def update_personal_data(
	payload: schemas.PersonalDataUpdate,
	request: Request,
):
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
)
async def replace_passport(
	payload: schemas.PassportPayload,
	request: Request,
):
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
)
async def update_contacts(
	payload: schemas.ContactsUpdate,
	request: Request,
):
	data = await forward_request(
		request,
		"PATCH",
		"/users/contacts",
		payload.model_dump(mode="json", exclude_unset=True),
	)
	return schemas.ContactsResponse.model_validate(data)
