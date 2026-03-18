import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import AsyncClient

from customer_service.main import app
from shared import schemas


@pytest.mark.asyncio
async def test_submit_personal_data_success(async_client: AsyncClient):
    """Проверка POST /personal-data — успех."""
    user_id = uuid.uuid4()
    payload = {"first_name": "Иван", "last_name": "Иванов", "birth_date": "1990-01-01", "gender": "M"}
    with patch("customer_service.create_account.router.service.store_personal_data", new_callable=AsyncMock) as mock:
        mock.return_value = schemas.PersonalDataResponse(client_id=user_id, **payload)
        response = await async_client.post(f"/users/{user_id}/account/personal-data", json=payload)
        assert response.status_code == 201


@pytest.mark.asyncio
async def test_send_email_code_success(async_client: AsyncClient):
    """Проверка /send-email-code — успех."""
    user_id = uuid.uuid4()
    mock_draft = {"payload": {"email": "test@example.com"}}
    with patch("customer_service.create_account.router.onboarding_drafts.load_draft", new_callable=AsyncMock, return_value=mock_draft), \
         patch("customer_service.create_account.router.save_email_code", new_callable=AsyncMock), \
         patch("customer_service.create_account.router.publish", new_callable=AsyncMock):
        
        response = await async_client.post(f"/users/{user_id}/account/send-email-code")
        assert response.status_code == 200
        assert "Код отправлен" in response.json()["message"]


@pytest.mark.asyncio
async def test_verify_email_success(async_client: AsyncClient):
    """Проверка /verify-email — успех."""
    user_id = uuid.uuid4()
    payload = {"code": "123456"}
    # Исправляем: передаем сам AsyncMock как замену, а не результат вызова factory
    with patch("customer_service.create_account.router.verify_email_code", AsyncMock(return_value=True)):
        response = await async_client.post(f"/users/{user_id}/account/verify-email", json=payload)
        assert response.status_code == 200
        assert response.json()["email_verified"] is True


@pytest.mark.asyncio
async def test_finalize_onboarding_full_success(async_client: AsyncClient):
    """Проверка /finalize — успех."""
    user_id = uuid.uuid4()
    with patch("customer_service.create_account.router.service.persist_onboarding_data", new_callable=AsyncMock), \
         patch("customer_service.create_account.router.publish", new_callable=AsyncMock):
        
        mock_session = AsyncMock()
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_session.get.return_value = mock_user
        
        from shared.database_core.db import get_session
        app.dependency_overrides[get_session] = lambda: mock_session
        try:
            response = await async_client.post(f"/users/{user_id}/account/finalize")
            assert response.status_code == 200
        finally:
            del app.dependency_overrides[get_session]
