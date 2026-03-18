import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from customer_service.create_account.service import (
    AccountDataConflict,
    AccountDataError,
    start_onboarding,
    store_personal_data,
    persist_onboarding_data,
)
from shared import models, schemas


@pytest.mark.asyncio
async def test_start_onboarding_success():
    session = MagicMock()
    session.get = AsyncMock(return_value=None)
    session.commit = AsyncMock()

    user_id = await start_onboarding(session)

    assert isinstance(user_id, uuid.UUID)
    session.add.assert_called_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_store_personal_data_success():
    session = MagicMock()
    session.get = AsyncMock(return_value=models.User(id=uuid.uuid4(), status="pending", is_verified=False))

    user_id = uuid.uuid4()
    payload = schemas.PersonalDataPayload(
        first_name="Иван",
        last_name="Иванов",
        birth_date="1990-01-01",
        gender="M",
    )

    with patch("customer_service.create_account.service.onboarding_drafts.save_draft", new_callable=AsyncMock) as mock_save_draft:
        response = await store_personal_data(session, user_id, payload)

        normalized_payload = schemas.PersonalDataPayload(
            first_name="ИВАН",
            last_name="ИВАНОВ",
            birth_date="1990-01-01",
            gender="M"
        )

        mock_save_draft.assert_called_once_with(
            user_id, "personal_data", normalized_payload.model_dump(mode="json")
        )
        assert response.client_id == user_id
        assert response.first_name == "ИВАН"


@pytest.mark.asyncio
async def test_store_personal_data_user_not_found():
    session = AsyncMock()
    session.get.return_value = None

    user_id = uuid.uuid4()
    payload = schemas.PersonalDataPayload(
        first_name="Иван",
        last_name="Иванов",
        birth_date="1990-01-01",
        gender="M",
    )

    with pytest.raises(AccountDataError, match="Сначала вызовите /users/start"):
        await store_personal_data(session, user_id, payload)


@pytest.mark.asyncio
async def test_persist_onboarding_data_missing_drafts():
    # Тест: если нет черновиков, должна быть ошибка
    session = AsyncMock()
    user_id = uuid.uuid4()

    with patch("customer_service.create_account.service.onboarding_drafts.load_draft", new_callable=AsyncMock) as mock_load_draft:
        mock_load_draft.return_value = None

        with pytest.raises(AccountDataError, match="Не заполнены или истекли черновики"):
            await persist_onboarding_data(session, user_id)
