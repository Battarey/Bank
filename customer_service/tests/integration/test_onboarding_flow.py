import os
import subprocess
from uuid import UUID, uuid4
from unittest.mock import AsyncMock
import pytest
from httpx import AsyncClient
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

@pytest.fixture(scope="session")
def postgres_container():
    """Starts a PostgreSQL container for integration testing."""
    # Ryuk (Reaper) can sometimes fail on Windows Docker Desktop.
    # If it fails, you can set TESTCONTAINERS_RYUK_DISABLED=true
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def postgres_url(postgres_container):
    """Returns the asyncpg URL for the postgres container."""
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    user = postgres_container.username
    password = postgres_container.password
    db = postgres_container.dbname
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

@pytest.fixture(scope="session", autouse=True)
def run_migrations(postgres_url, postgres_container):
    """Runs alembic migrations on the test container."""
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    user = postgres_container.username
    password = postgres_container.password
    db = postgres_container.dbname
    sync_url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
    
    os.environ["ALEMBIC_DATABASE_URL"] = sync_url
    
    migrations_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../migrations"))
    subprocess.run(
        ["alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=migrations_dir,
        check=True,
        capture_output=True
    )
    yield

@pytest.mark.asyncio
async def test_full_onboarding_integration(async_client: AsyncClient, postgres_url, mocker):
    """Integration test for the complete onboarding flow."""
    from shared.database_core import db
    from customer_service.main import app
    from shared.database_core.db import get_session

    engine = create_async_engine(postgres_url)
    TestingSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def override_get_session():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    # In-memory store for drafts to simulate Redis behavior across multiple requests
    drafts_store = {}

    async def mock_save_draft(user_id, step, payload):
        drafts_store[(str(user_id), step)] = payload

    async def mock_load_draft(user_id, step):
        payload = drafts_store.get((str(user_id), step))
        if payload:
            return {"payload": payload}
        return None
    
    async def mock_clear_all(user_id):
        keys_to_del = [k for k in drafts_store.keys() if k[0] == str(user_id)]
        for k in keys_to_del:
            del drafts_store[k]

    mocker.patch("shared.redis_onboarding.drafts.save_draft", side_effect=mock_save_draft)
    mocker.patch("shared.redis_onboarding.drafts.load_draft", side_effect=mock_load_draft)
    mocker.patch("shared.redis_onboarding.drafts.clear_all", side_effect=mock_clear_all)
    mocker.patch("shared.redis_onboarding.email_codes.is_email_verified", return_value=True)
    mocker.patch("shared.redis_onboarding.email_codes.clear_email_verification", new_callable=AsyncMock)
    mocker.patch("shared.rabbitmq.publish", new_callable=AsyncMock)

    headers = {"X-Internal-Key": "test-key"}

    # 1. Start onboarding
    resp = await async_client.post("/users/start", headers=headers)
    assert resp.status_code == 201
    user_id = resp.json()["user_id"]
    
    # 2. Submit Personal Data
    payload = {
        "first_name": "ИВАН",
        "last_name": "ИВАНОВ",
        "birth_date": "1990-01-01",
        "gender": "M"
    }
    resp = await async_client.post(f"/users/{user_id}/account/personal-data", json=payload, headers=headers)
    assert resp.status_code == 201
    
    # 3. Submit Passport
    payload = {
        "series": "1234",
        "number": "567890",
        "division_code": "123-456",
        "issued_by": "ОТДЕЛ УФМС",
        "issued_at": "2010-01-01",
        "expiration_date": "2030-01-01",
        "registration_address": "г. Москва"
    }
    resp = await async_client.post(f"/users/{user_id}/account/passport", json=payload, headers=headers)
    assert resp.status_code == 201

    # 4. Submit Identifiers
    payload = {
        "inn": "123456789012",
        "snils": "12345678901"
    }
    resp = await async_client.post(f"/users/{user_id}/account/identifiers", json=payload, headers=headers)
    assert resp.status_code == 201

    # 5. Submit Contacts
    payload = {
        "email": "test@example.com",
        "phone": "+79991234567"
    }
    resp = await async_client.post(f"/users/{user_id}/account/contacts", json=payload, headers=headers)
    assert resp.status_code == 201

    # 6. Finalize
    resp = await async_client.post(f"/users/{user_id}/account/finalize", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    # Verify data in DB
    async with TestingSessionLocal() as session:
        from shared import models
        from sqlalchemy import select
        user = await session.get(models.User, UUID(user_id))
        assert user.status == "active"
        
        personal = await session.get(models.PersonalData, UUID(user_id))
        assert personal.first_name == "ИВАН"

    app.dependency_overrides.clear()

