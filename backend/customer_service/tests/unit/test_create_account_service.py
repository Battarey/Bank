import pytest
from uuid import uuid4
from datetime import UTC, datetime, date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from customer_service.create_account.service import (
    start_onboarding,
    store_personal_data,
    store_passport_data,
    store_identifiers,
    store_contacts,
    persist_onboarding_data,
)
from customer_service.exceptions import (
    OnboardingError,
    OnboardingConflict,
    OnboardingNotFound,
)
from shared import models, schemas


@pytest.mark.asyncio
async def test_start_onboarding_success(uow):
    """Успешное начало онбординга."""
    uow.customers.get.return_value = None
    
    user_id = await start_onboarding(uow)
    
    assert isinstance(user_id, uuid4().__class__)
    uow.customers.add.assert_called_once()
    assert uow.committed is True


@pytest.mark.asyncio
async def test_start_onboarding_failure(uow):
    """Ошибка начала онбординга при коллизиях UUID."""
    uow.customers.get.return_value = models.User(id=uuid4())
    
    with pytest.raises(OnboardingError, match="Не удалось инициализировать"):
        await start_onboarding(uow)


@pytest.mark.asyncio
async def test_store_personal_data_success(uow):
    """Успешное сохранение персональных данных (черновик)."""
    user_id = uuid4()
    payload = schemas.PersonalDataPayload(
        first_name="иван",
        last_name="иванов",
        middle_name="иванович",
        birth_date=date(1990, 1, 1),
        gender="M",
    )
    uow.customers.get_active_user.return_value = models.User(id=user_id)
    
    with patch("customer_service.create_account.service.onboarding_drafts.save_draft", AsyncMock()) as mock_save:
        res = await store_personal_data(uow, user_id, payload)
        
        assert res.first_name == "ИВАН"
        assert res.last_name == "ИВАНОВ"
        mock_save.assert_called_once()


@pytest.mark.asyncio
async def test_persist_onboarding_data_success(uow):
    """Успешная финализация онбординга."""
    user_id = uuid4()
    user = models.User(id=user_id, status="pending")
    uow.customers.get_active_user.return_value = user
    
    drafts = {
        "personal_data": {"payload": {"first_name": "Иван", "last_name": "Иванов", "birth_date": "1990-01-01", "gender": "M"}},
        "passport": {"payload": {
            "series": "1234", "number": "123456", "issued_by": "ОВД", 
            "issued_at": "2010-01-01", "expiration_date": "2030-01-01", 
            "division_code": "111-123", "registration_address": "MSC"
        }},
        "identifiers": {"payload": {"inn": "123456789012", "snils": "12345678901"}},
        "contacts": {"payload": {"email": "test@test.com", "phone": "+79991234567"}},
    }
    
    with patch("customer_service.create_account.service.onboarding_drafts.load_draft", AsyncMock(side_effect=lambda uid, step: drafts.get(step))), \
         patch("customer_service.create_account.service.is_email_verified", AsyncMock(return_value=True)), \
         patch("customer_service.create_account.service.onboarding_drafts.clear_all", AsyncMock()), \
         patch("customer_service.create_account.service.clear_email_verification", AsyncMock()):
        
        await persist_onboarding_data(uow, user_id)
        
        assert user.status == "active"
        assert uow.committed is True
        # Проверка регистрации событий
        assert len(uow.events) == 2
        assert uow.events[0].action == "registration"
        assert uow.events[1].type == "registration_success"


@pytest.mark.asyncio
async def test_persist_onboarding_data_missing_steps(uow):
    """Ошибка финализации: не все шаги заполнены."""
    user_id = uuid4()
    with patch("customer_service.create_account.service.onboarding_drafts.load_draft", AsyncMock(return_value=None)):
        with pytest.raises(OnboardingError, match="Не все шаги онбординга завершены"):
            await persist_onboarding_data(uow, user_id)
