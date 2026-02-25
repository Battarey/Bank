"""Маршруты customer_service — онбординг, управление пользователями."""

from uuid import UUID
from fastapi import APIRouter, Request, status
from shared import schemas
from ..helpers import forward_request

router = APIRouter(tags=["onboarding"])


@router.post(
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


@router.post(
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


@router.post(
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


@router.post(
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


@router.post(
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


@router.post(
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
