import pytest
from fastapi.testclient import TestClient
from metal_service.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check(client):
    """Проверка эндпоинта health_check."""
    
    internal_key = "super-secret-internal-key-change-me" # Значение из .env local для теста
    response = client.get("/health", headers={"X-Internal-Key": internal_key})
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["dependencies"]["external_metal_api"] == "ok"
