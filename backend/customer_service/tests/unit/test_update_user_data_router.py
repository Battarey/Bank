import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import HTTPException

from customer_service.update_user_data import service
from customer_service.update_user_data.router import _run, update_personal_data, replace_passport, update_contacts
from shared import schemas

@pytest.mark.asyncio
async def test_run_success():
    async def step():
        return "ok"
    res = await _run(step, AsyncMock())
    assert res == "ok"

@pytest.mark.asyncio
async def test_run_exceptions():
    session = AsyncMock()
    
    async def raise_not_found():
        raise service.UpdateDataNotFound("nof")
    with pytest.raises(HTTPException) as exc:
        await _run(raise_not_found, session)
    assert exc.value.status_code == 404
    
    async def raise_conflict():
        raise service.UpdateDataConflict("conf")
    with pytest.raises(HTTPException) as exc:
        await _run(raise_conflict, session)
    assert exc.value.status_code == 409
    session.rollback.assert_awaited_once()
    
    async def raise_empty():
        raise service.UpdateDataEmpty("emp")
    with pytest.raises(HTTPException) as exc:
        await _run(raise_empty, session)
    assert exc.value.status_code == 422
    
    async def raise_error():
        raise service.UpdateDataError("err")
    with pytest.raises(HTTPException) as exc:
        await _run(raise_error, session)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
@patch("customer_service.update_user_data.router.service.update_personal_data", new_callable=AsyncMock)
async def test_router_update_personal_data(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    payload = schemas.PersonalDataUpdate(first_name="Ivan")
    
    mock_svc.return_value = schemas.PersonalDataResponse(client_id=user_id, first_name="IVAN", last_name="IVANOV", middle_name=None, birth_date="1990-01-01", gender="M")
    
    res = await update_personal_data(payload=payload, user_id=user_id, session=session)
    assert res.first_name == "IVAN"
    mock_svc.assert_awaited_once_with(session, user_id, payload)


@pytest.mark.asyncio
@patch("customer_service.update_user_data.router.service.replace_passport", new_callable=AsyncMock)
async def test_router_replace_passport(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    payload = schemas.PassportPayload(series="1234", number="123456", issued_by="UVD", issued_at="2010-01-01", expiration_date="2030-01-01", division_code="123-456", registration_address="MSC")
    
    mock_svc.return_value = schemas.PassportResponse(client_id=user_id, **payload.model_dump())
    
    res = await replace_passport(payload=payload, user_id=user_id, session=session)
    assert res.series == "1234"
    mock_svc.assert_awaited_once_with(session, user_id, payload)


@pytest.mark.asyncio
@patch("customer_service.update_user_data.router.service.update_contacts", new_callable=AsyncMock)
async def test_router_update_contacts(mock_svc):
    session = AsyncMock()
    user_id = uuid4()
    payload = schemas.ContactsUpdate(email="a@b.com")
    
    mock_svc.return_value = schemas.ContactsResponse(client_id=user_id, email="a@b.com", phone="+79991234567")
    
    res = await update_contacts(payload=payload, user_id=user_id, session=session)
    assert res.email == "a@b.com"
    mock_svc.assert_awaited_once_with(session, user_id, payload)
