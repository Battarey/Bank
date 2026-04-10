from datetime import UTC, date, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from customer_service.exceptions import (
    UpdateDataConflict,
    UpdateDataError,
    UpdateDataNotFound,
)
from customer_service.update_user_data.service import (
    _get_active_user,
    get_full_profile,
    replace_passport,
    update_contacts,
    update_personal_data,
)
from shared import models, schemas


@pytest.mark.asyncio
async def test_get_active_user_not_found(uow):
    """Пользователь не найден."""
    uow.customers.get_active_user.side_effect = UpdateDataNotFound("not found")
    with pytest.raises(UpdateDataNotFound):
        await _get_active_user(uow, uuid4())


@pytest.mark.asyncio
async def test_get_active_user_not_active(uow):
    """Пользователь не в статусе active."""
    user = models.User(status="frozen")
    uow.customers.get_active_user.return_value = user
    with pytest.raises(UpdateDataError, match="Обновление данных запрещено"):
        await _get_active_user(uow, uuid4())


@pytest.mark.asyncio
async def test_update_personal_data_success(uow):
    """Успешное обновление ФИО."""
    user_id = uuid4()
    payload = schemas.PersonalDataUpdate(first_name="  ivan ", last_name="Ivanov")
    user = models.User(status="active")
    record = models.PersonalData(
        client_id=user_id, 
        first_name="O", 
        last_name="O", 
        middle_name="O",
        birth_date=date(1990, 1, 1),
        gender="M"
    )
    
    uow.customers.get_active_user.return_value = user
    uow.customers.get_personal_data.return_value = record
    
    res = await update_personal_data(uow, user_id, payload)
    
    assert record.first_name == "IVAN"
    assert record.last_name == "IVANOV"
    assert uow.committed is True
    assert res.first_name == "IVAN"
    assert len(uow.events) == 1
    assert uow.events[0].action == "update_personal_data"


@pytest.mark.asyncio
async def test_replace_passport_success(uow):
    """Успешная замена паспорта."""
    user_id = uuid4()
    payload = schemas.PassportPayload(
        series="1234", number="123456", issued_by=" UVD ", 
        issued_at="2000-01-01", expiration_date="2040-01-01", 
        division_code="123-456", registration_address=" MSC "
    )
    user = models.User(status="active")
    record = models.Passport(client_id=user_id)
    
    uow.customers.get_active_user.return_value = user
    uow.customers.get_passport.return_value = record
    
    res = await replace_passport(uow, user_id, payload)
    
    assert record.issued_by == "UVD"
    assert uow.committed is True
    assert uow.events[0].action == "replace_passport"


@pytest.mark.asyncio
async def test_update_contacts_conflict(uow):
    """Конфликт при обновлении контактов."""
    user_id = uuid4()
    payload = schemas.ContactsUpdate(email="a@b.com")
    uow.customers.get_active_user.return_value = models.User(status="active")
    uow.customers.get_contact.return_value = models.Contact(client_id=user_id)
    
    uow.commit = AsyncMock(side_effect=IntegrityError("a", "b", "c"))
    
    with pytest.raises(UpdateDataConflict):
        await update_contacts(uow, user_id, payload)


@pytest.mark.asyncio
async def test_get_full_profile_success(uow):
    """Успешное получение полного профиля (CQRS)."""
    user_id = uuid4()
    expected_profile = schemas.FullProfileResponse(
        id=user_id, status="active", created_at=datetime.now(UTC),
        first_name="Ivan", last_name="Ivanov", middle_name=None,
        birth_date=date(1990, 1, 1), gender="M",
        email="ivan@test.com", phone="+79991234567",
        passport_series="1234", passport_number="123456",
        inn="123456789012", snils="12345678901"
    )
    uow.customer_queries.get_full_profile.return_value = expected_profile
    
    res = await get_full_profile(uow, user_id)
    
    assert res == expected_profile
    uow.customer_queries.get_full_profile.assert_called_once_with(user_id)
