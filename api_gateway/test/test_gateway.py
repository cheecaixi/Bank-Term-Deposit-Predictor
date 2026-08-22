# Test the FastAPI application without starting a separate server process.
from fastapi.testclient import TestClient
from app.main import app

# Reuse one client for the lightweight health and root endpoint tests.
client = TestClient(app)

def test_health_check():
    # Kubernetes health checks should receive the expected response.
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "api-gateway"}

def test_read_root():
    # The root endpoint should expose a basic gateway status message.
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()