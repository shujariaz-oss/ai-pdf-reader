import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_upload_endpoint_rejection_on_invalid_format():
    response = client.post("/api/upload", files={"file": ("test.txt", b"hello world", "text/plain")})
    assert response.status_code == 400
