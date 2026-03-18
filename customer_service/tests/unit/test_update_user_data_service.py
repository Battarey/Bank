import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from customer_service.update_user_data.service import (
    UpdateDataConflict,
    UpdateDataEmpty,
    UpdateDataError,
    UpdateDataNotFound,
    _get_active_user,
    replace_passport,
    update_contacts,
    update_personal_data,
)
from shared import models, schemas
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.scalar = AsyncMock()
    session.execute = AsyncMock()
    return session

@pytest.mark.asyncio
async def test_get_active_user_not_found(mock_session):
    mock_session.get.return_value = None
    with pytest.raises(UpdateDataNotFound):
        await _get_active_user(mock_session, uuid4())

@pytest.mark.asyncio
async def test_get_active_user_not_active(mock_session):
    user = models.User(status="frozen")
    mock_session.get.return_value = user
    with pytest.raises(UpdateDataError):
        await _get_active_user(mock_session, uuid4())

@pytest.mark.asyncio
async def test_get_active_user_success(mock_session):
    user = models.User(status="active")
    mock_session.get.return_value = user
    result = await _get_active_user(mock_session, uuid4())
    assert result == user


@pytest.mark.asyncio
async def test_update_personal_data_empty(mock_session):
    payload = schemas.PersonalDataUpdate()
    with pytest.raises(UpdateDataEmpty):
        await update_personal_data(mock_session, uuid4(), payload)

@pytest.mark.asyncio
async def test_update_personal_data_not_found(mock_session):
    payload = schemas.PersonalDataUpdate(first_name="Ivan")
    # _get_active_user -> returns user, session.get(PersonalData) -> None
    def side_effect(model, pk):
        if model == models.User:
            return models.User(status="active")
        return None
    mock_session.get.side_effect = side_effect
    
    with pytest.raises(UpdateDataNotFound):
        await update_personal_data(mock_session, uuid4(), payload)

@pytest.mark.asyncio
async def test_update_personal_data_success(mock_session):
    payload = schemas.PersonalDataUpdate(first_name="  ivan ", last_name="Ivanov")
    user = models.User(status="active")
    record = models.PersonalData(client_id=uuid4(), first_name="O", last_name="O", middle_name="O", birth_date="2000-01-01", gender="M")
    
    def side_effect(model, pk):
        if model == models.User:
            return user
        if model == models.PersonalData:
            return record
        return None
    mock_session.get.side_effect = side_effect
    
    res = await update_personal_data(mock_session, uuid4(), payload)
    
    assert record.first_name == "IVAN"
    assert record.last_name == "IVANOV"
    assert record.middle_name == "O"
    mock_session.commit.assert_awaited_once()
    assert res.first_name == "IVAN"

@pytest.mark.asyncio
async def test_update_personal_data_db_error(mock_session):
    payload = schemas.PersonalDataUpdate(first_name="Ivan")
    def side_effect(model, pk):
        if model == models.User:
            return models.User(status="active")
        if model == models.PersonalData:
            return models.PersonalData()
    mock_session.get.side_effect = side_effect
    mock_session.commit.side_effect = Exception("error")
    
    with pytest.raises(Exception):
        await update_personal_data(mock_session, uuid4(), payload)
    mock_session.rollback.assert_awaited_once()

# Passport tests
@pytest.mark.asyncio
async def test_replace_passport_duplicate_scalar(mock_session):
    payload = schemas.PassportPayload(series="1234", number="123456", issued_by="UVD", issued_at="2000-01-01", expiration_date="2040-01-01", division_code="123-456", registration_address="MSC")
    user_id = uuid4()
    def side_effect(model, pk):
        if model == models.User:
            return models.User(status="active")
        if model == models.Passport:
            return models.Passport()
    mock_session.get.side_effect = side_effect
    
    duplicate_passport = models.Passport(client_id=uuid4()) # Another client
    mock_session.scalar.return_value = duplicate_passport
    
    with pytest.raises(UpdateDataConflict, match="уже привязан"):
        await replace_passport(mock_session, user_id, payload)


@pytest.mark.asyncio
async def test_replace_passport_success(mock_session):
    payload = schemas.PassportPayload(
        series="1234", number="123456", issued_by=" UVD ", 
        issued_at="2000-01-01", expiration_date="2040-01-01", 
        division_code="123-456", registration_address=" MSC "
    )
    user_id = uuid4()
    record = models.Passport(client_id=user_id)
    def side_effect(model, pk):
        if model == models.User:
            return models.User(status="active")
        if model == models.Passport:
            return record
    mock_session.get.side_effect = side_effect
    mock_session.scalar.return_value = None # No duplicates
    
    res = await replace_passport(mock_session, user_id, payload)
    
    assert record.issued_by == "UVD"
    assert record.registration_address == "MSC"
    assert res.issued_by == "UVD"
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_replace_passport_integrity_error(mock_session):
    payload = schemas.PassportPayload(series="1234", number="123456", issued_by="UVD", issued_at="2000-01-01", expiration_date="2040-01-01", division_code="123-456", registration_address="MSC")
    user_id = uuid4()
    def side_effect(model, pk):
        if model == models.User:
            return models.User(status="active")
        if model == models.Passport:
            return models.Passport()
    mock_session.get.side_effect = side_effect
    mock_session.scalar.return_value = None
    mock_session.commit.side_effect = IntegrityError("a", "b", "c")
    
    with pytest.raises(UpdateDataConflict):
        await replace_passport(mock_session, user_id, payload)
    mock_session.rollback.assert_awaited_once()

# Contacts tests
@pytest.mark.asyncio
async def test_update_contacts_empty(mock_session):
    with pytest.raises(UpdateDataEmpty):
        await update_contacts(mock_session, uuid4(), schemas.ContactsUpdate())

@pytest.mark.asyncio
async def test_update_contacts_success(mock_session):
    payload = schemas.ContactsUpdate(email=" A@b.com ", phone="+79991234567")
    user_id = uuid4()
    record = models.Contact(client_id=user_id)
    def side_effect(model, pk):
        if model == models.User:
            return models.User(status="active")
        if model == models.Contact:
            return record
    mock_session.get.side_effect = side_effect
    mock_session.scalar.return_value = None
    
    res = await update_contacts(mock_session, user_id, payload)
    assert record.email == "a@b.com"
    assert record.phone == "+79991234567"
    assert res.email == "a@b.com"

@pytest.mark.asyncio
async def test_update_contacts_integrity_error(mock_session):
    payload = schemas.ContactsUpdate(email="a@b.com")
    def side_effect(model, pk):
        if model == models.User:
            return models.User(status="active")
        if model == models.Contact:
            return models.Contact()
    mock_session.get.side_effect = side_effect
    mock_session.scalar.return_value = None
    mock_session.commit.side_effect = IntegrityError("a", "b", "c")
    
    with pytest.raises(UpdateDataConflict):
        await update_contacts(mock_session, uuid4(), payload)
