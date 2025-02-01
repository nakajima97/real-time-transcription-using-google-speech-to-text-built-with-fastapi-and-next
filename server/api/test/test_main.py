from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_dummy():
    response = client.get("/")
    assert response.status_code == 200
