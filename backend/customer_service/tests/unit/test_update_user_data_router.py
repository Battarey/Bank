from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from customer_service.update_user_data.router import (
	get_my_profile,
	replace_passport,
	update_contacts,
	update_personal_data,
)
from shared import schemas


@pytest.mark.asyncio
@patch("customer_service.update_user_data.router.service.get_full_profile", new_callable=AsyncMock)
async def test_router_get_my_profile(mock_svc, uow):
	"""Роутер: получение профиля текущего пользователя."""
	user_id = uuid4()
	mock_svc.return_value = schemas.FullProfileResponse(
		id=user_id,
		status="active",
		created_at=datetime.now(UTC),
		first_name="Ivan",
		last_name="Ivanov",
		middle_name=None,
		birth_date=date(1990, 1, 1),
		gender="M",
		email="ivan@test.com",
		phone="+79991234567",
		passport_series="1234",
		passport_number="123456",
		inn="123456789012",
		snils="12345678901",
	)

	res = await get_my_profile(user_id=user_id, uow=uow)

	assert res.first_name == "Ivan"
	mock_svc.assert_awaited_once_with(uow, user_id)


@pytest.mark.asyncio
@patch("customer_service.update_user_data.router.service.update_personal_data", new_callable=AsyncMock)
async def test_router_update_personal_data(mock_svc, uow):
	"""Роутер: обновление ФИО."""
	user_id = uuid4()
	payload = schemas.PersonalDataUpdate(first_name="Ivan")
	mock_svc.return_value = schemas.PersonalDataResponse(
		client_id=user_id, first_name="IVAN", last_name="IVANOV", birth_date="1990-01-01", gender="M"
	)

	res = await update_personal_data(payload=payload, user_id=user_id, uow=uow)

	assert res.first_name == "IVAN"
	mock_svc.assert_awaited_once_with(uow, user_id, payload)


@pytest.mark.asyncio
@patch("customer_service.update_user_data.router.service.replace_passport", new_callable=AsyncMock)
async def test_router_replace_passport(mock_svc, uow):
	"""Роутер: замена паспорта."""
	user_id = uuid4()
	payload = schemas.PassportPayload(
		series="1234",
		number="123456",
		issued_by="UVD",
		issued_at="2010-01-01",
		expiration_date="2030-01-01",
		division_code="123-456",
		registration_address="MSC",
	)
	mock_svc.return_value = schemas.PassportResponse(client_id=user_id, **payload.model_dump())

	res = await replace_passport(payload=payload, user_id=user_id, uow=uow)

	assert res.series == "1234"
	mock_svc.assert_awaited_once_with(uow, user_id, payload)


@pytest.mark.asyncio
@patch("customer_service.update_user_data.router.service.update_contacts", new_callable=AsyncMock)
async def test_router_update_contacts(mock_svc, uow):
	"""Роутер: обновление контактов."""
	user_id = uuid4()
	payload = schemas.ContactsUpdate(email="a@b.com")
	mock_svc.return_value = schemas.ContactsResponse(client_id=user_id, email="a@b.com", phone="+79991234567")

	res = await update_contacts(payload=payload, user_id=user_id, uow=uow)

	assert res.email == "a@b.com"
	mock_svc.assert_awaited_once_with(uow, user_id, payload)
