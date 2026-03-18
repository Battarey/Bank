from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
from customer_service.main import app
from shared.database_core.db import get_session

@pytest.mark.asyncio
async def test_start_endpoint_success(async_client: AsyncClient):
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    with patch("customer_service.create_account.router.service.start_onboarding", new_callable=AsyncMock) as mock_start:
        mock_start.return_value = "123e4567-e89b-12d3-a456-426614174000"

        headers = {"X-Internal-Key": "test-key"}
        response = await async_client.post("/users/start", headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == "123e4567-e89b-12d3-a456-426614174000"

    app.dependency_overrides.pop(get_session)


@pytest.mark.asyncio
async def test_start_endpoint_no_internal_key(async_client: AsyncClient):
    from shared.internal_auth import verify_internal_key
    
    original_override = app.dependency_overrides.get(verify_internal_key)
    app.dependency_overrides.pop(verify_internal_key, None)
    
    try:
        response = await async_client.post("/users/start")
        assert response.status_code == 403 or response.status_code == 422
    finally:
        if original_override:
            app.dependency_overrides[verify_internal_key] = original_override
