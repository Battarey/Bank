from datetime import date
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from customer_service.create_account.router import (
	complete_onboarding,
	start_onboarding,
	store_personal_data,
)
from shared import schemas


@pytest.mark.asyncio
@patch("customer_service.create_account.router.service.start_onboarding", new_callable=AsyncMock)
async def test_router_start_onboarding(mock_svc, uow):
	"""Роутер: начало онбординга."""
	user_id = uuid4()
	mock_svc.return_value = user_id

	res = await start_onboarding(uow=uow)

	assert res.user_id == user_id
	assert res.status == "pending"
	mock_svc.assert_awaited_once_with(uow)


@pytest.mark.asyncio
@patch("customer_service.create_account.router.service.store_personal_data", new_callable=AsyncMock)
async def test_router_store_personal_data(mock_svc, uow):
	"""Роутер: сохранение персональных данных."""
	user_id = uuid4()
	payload = schemas.PersonalDataPayload(
		first_name="Ivan", last_name="Ivanov", birth_date=date(1990, 1, 1), gender="M"
	)
	mock_svc.return_value = schemas.PersonalDataResponse(
		client_id=user_id, first_name="IVAN", last_name="IVANOV", birth_date=date(1990, 1, 1), gender="M"
	)

	res = await store_personal_data(user_id=user_id, payload=payload, uow=uow)

	assert res.client_id == user_id
	mock_svc.assert_awaited_once_with(uow, user_id, payload)


@pytest.mark.asyncio
@patch("customer_service.create_account.router.service.persist_onboarding_data", new_callable=AsyncMock)
async def test_router_complete_onboarding(mock_svc, uow):
	"""Роутер: завершение онбординга."""
	user_id = uuid4()

	res = await complete_onboarding(user_id=user_id, uow=uow)

	assert res.status == "completed"
	assert "успешно завершена" in res.message
	mock_svc.assert_awaited_once_with(uow, user_id)
