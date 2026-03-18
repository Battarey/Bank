import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from customer_service.create_account.service import (
    AccountDataConflict,
    AccountDataError,
    store_passport_data,
    store_identifiers,
    store_contacts,
    persist_onboarding_data,
    start_onboarding,
    store_personal_data,
)
from shared import models, schemas


@pytest.fixture
def mock_session():
    """Фикстура для мока сессии БД."""
    session = MagicMock()
    session.get = AsyncMock(return_value=None)
    session.scalar = AsyncMock(return_value=None)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    
    session._db_state = {}
    async def get_side_effect(model, ident):
        return session._db_state.get((model, ident))
    session.get.side_effect = get_side_effect
    
    return session


@pytest.mark.asyncio
async def test_start_onboarding_failure_exhausted(mock_session):
    """Проверка исчерпания попыток генерации UUID."""
    mock_session.get.side_effect = None
    mock_session.get.return_value = models.User(id=uuid.uuid4())
    with pytest.raises(AccountDataError, match="Не удалось создать"):
        await start_onboarding(mock_session)


@pytest.mark.asyncio
async def test_store_personal_data_success_normalized(mock_session):
    """Успешное сохранение персональных данных с нормализацией."""
    user_id = uuid.uuid4()
    mock_session._db_state[(models.User, user_id)] = models.User(id=user_id)
    payload = schemas.PersonalDataPayload(
        first_name="иван", 
        last_name="иванов", 
        birth_date=date(1990, 1, 1), 
        gender="M"
    )
    with patch("customer_service.create_account.service.onboarding_drafts.save_draft", new_callable=AsyncMock):
        res = await store_personal_data(mock_session, user_id, payload)
        assert res.first_name == "ИВАН"


def get_full_payloads():
    """Возвращает полный набор валидных данных для всех шагов."""
    return {
        "personal_data": {"first_name": "Иван", "last_name": "Иванов", "birth_date": "1990-01-01", "gender": "M"},
        "passport": {
            "series": "1234", "number": "123456", "issued_by": "ОВД", 
            "issued_at": "2010-01-01", "expiration_date": "2030-01-01", 
            "division_code": "111-123", "registration_address": "Ул. Пушкина"
        },
        "identifiers": {"inn": "123456789012", "snils": "12345678901"},
        "contacts": {"email": "test@example.com", "phone": "+79991234567"}
    }


@pytest.mark.asyncio
async def test_persist_onboarding_data_personal_conflict(mock_session):
    """Конфликт: персональные данные уже есть в БД."""
    user_id = uuid.uuid4()
    mock_session._db_state[(models.User, user_id)] = models.User(id=user_id)
    mock_session._db_state[(models.PersonalData, user_id)] = models.PersonalData(client_id=user_id)
    
    payloads = get_full_payloads()
    with patch("customer_service.create_account.service.onboarding_drafts.load_draft", new_callable=AsyncMock) as m_load, \
         patch("customer_service.create_account.service.is_email_verified", AsyncMock(return_value=True)):
        m_load.side_effect = lambda uid, step: {"payload": payloads[step]}
        with pytest.raises(AccountDataConflict, match="Personal data already captured"):
            await persist_onboarding_data(mock_session, user_id)


@pytest.mark.asyncio
async def test_persist_onboarding_data_passport_record_conflict(mock_session):
    """Конфликт: данные паспорта уже есть в БД."""
    user_id = uuid.uuid4()
    mock_session._db_state[(models.User, user_id)] = models.User(id=user_id)
    mock_session._db_state[(models.Passport, user_id)] = models.Passport(client_id=user_id)
    
    payloads = get_full_payloads()
    with patch("customer_service.create_account.service.onboarding_drafts.load_draft", new_callable=AsyncMock) as m_load, \
         patch("customer_service.create_account.service.is_email_verified", AsyncMock(return_value=True)):
        m_load.side_effect = lambda uid, step: {"payload": payloads[step]}
        with pytest.raises(AccountDataConflict, match="Passport data already captured"):
            await persist_onboarding_data(mock_session, user_id)


@pytest.mark.asyncio
async def test_persist_onboarding_data_passport_unique_conflict(mock_session):
    """Конфликт: серия/номер паспорта уже заняты другим клиентом."""
    user_id = uuid.uuid4()
    mock_session._db_state[(models.User, user_id)] = models.User(id=user_id)
    async def scalar_side_effect(stmt):
        if "passport" in str(stmt).lower():
            return models.Passport(client_id=uuid.uuid4())
        return None
    mock_session.scalar.side_effect = scalar_side_effect
    
    payloads = get_full_payloads()
    with patch("customer_service.create_account.service.onboarding_drafts.load_draft", new_callable=AsyncMock) as m_load, \
         patch("customer_service.create_account.service.is_email_verified", AsyncMock(return_value=True)):
        m_load.side_effect = lambda uid, step: {"payload": payloads[step]}
        with pytest.raises(AccountDataConflict, match="Passport is already linked"):
            await persist_onboarding_data(mock_session, user_id)


@pytest.mark.asyncio
async def test_persist_onboarding_data_identifiers_record_conflict(mock_session):
    """Конфликт: идентификаторы уже есть в БД."""
    user_id = uuid.uuid4()
    mock_session._db_state[(models.User, user_id)] = models.User(id=user_id)
    mock_session._db_state[(models.Identifier, user_id)] = models.Identifier(client_id=user_id)
    
    payloads = get_full_payloads()
    with patch("customer_service.create_account.service.onboarding_drafts.load_draft", new_callable=AsyncMock) as m_load, \
         patch("customer_service.create_account.service.is_email_verified", AsyncMock(return_value=True)):
        m_load.side_effect = lambda uid, step: {"payload": payloads[step]}
        with pytest.raises(AccountDataConflict, match="Identifiers already captured"):
            await persist_onboarding_data(mock_session, user_id)


@pytest.mark.asyncio
async def test_persist_onboarding_data_identifiers_unique_conflict(mock_session):
    """Конфликт: ИНН/СНИЛС уже заняты другим клиентом."""
    user_id = uuid.uuid4()
    mock_session._db_state[(models.User, user_id)] = models.User(id=user_id)
    async def scalar_side_effect(stmt):
        if "identifier" in str(stmt).lower():
            return models.Identifier(client_id=uuid.uuid4())
        return None
    mock_session.scalar.side_effect = scalar_side_effect
    
    payloads = get_full_payloads()
    with patch("customer_service.create_account.service.onboarding_drafts.load_draft", new_callable=AsyncMock) as m_load, \
         patch("customer_service.create_account.service.is_email_verified", AsyncMock(return_value=True)):
        m_load.side_effect = lambda uid, step: {"payload": payloads[step]}
        with pytest.raises(AccountDataConflict, match="Provided INN or SNILS already belongs"):
            await persist_onboarding_data(mock_session, user_id)


@pytest.mark.asyncio
async def test_persist_onboarding_data_contacts_unique_conflict(mock_session):
    """Конфликт: email или телефон уже заняты."""
    user_id = uuid.uuid4()
    mock_session._db_state[(models.User, user_id)] = models.User(id=user_id)
    async def scalar_side_effect(stmt):
        if "contact" in str(stmt).lower():
            return models.Contact(client_id=uuid.uuid4())
        return None
    mock_session.scalar.side_effect = scalar_side_effect
    
    payloads = get_full_payloads()
    with patch("customer_service.create_account.service.onboarding_drafts.load_draft", new_callable=AsyncMock) as m_load, \
         patch("customer_service.create_account.service.is_email_verified", AsyncMock(return_value=True)):
        
        m_load.side_effect = lambda uid, step: {"payload": payloads[step]}
        with pytest.raises(AccountDataConflict, match="email or phone already belongs"):
            await persist_onboarding_data(mock_session, user_id)


@pytest.mark.asyncio
async def test_persist_onboarding_data_email_not_verified(mock_session):
    """Ошибка: email не подтвержден."""
    user_id = uuid.uuid4()
    mock_session._db_state[(models.User, user_id)] = models.User(id=user_id)
    
    payloads = get_full_payloads()
    with patch("customer_service.create_account.service.onboarding_drafts.load_draft", new_callable=AsyncMock) as m_load, \
         patch("customer_service.create_account.service.is_email_verified", AsyncMock(return_value=False)):
        
        m_load.side_effect = lambda uid, step: {"payload": payloads[step]}
        with pytest.raises(AccountDataError, match="Email не подтверждён"):
            await persist_onboarding_data(mock_session, user_id)


@pytest.mark.asyncio
async def test_persist_onboarding_data_success_full(mock_session):
    """Полный цикл финализации — успех."""
    user_id = uuid.uuid4()
    user = models.User(id=user_id, status="pending")
    mock_session._db_state[(models.User, user_id)] = user
    
    payloads = get_full_payloads()
    with patch("customer_service.create_account.service.onboarding_drafts.load_draft", new_callable=AsyncMock) as m_load, \
         patch("customer_service.create_account.service.is_email_verified", AsyncMock(return_value=True)), \
         patch("customer_service.create_account.service.onboarding_drafts.clear_all", new_callable=AsyncMock), \
         patch("customer_service.create_account.service.clear_email_verification", new_callable=AsyncMock), \
         patch("customer_service.create_account.service.publish", new_callable=AsyncMock):
        
        m_load.side_effect = lambda uid, step: {"payload": payloads[step]}
        await persist_onboarding_data(mock_session, user_id)
        assert user.status == "active"
        mock_session.commit.assert_awaited()
