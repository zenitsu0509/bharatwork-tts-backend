"""Simple tests for the English-to-Hindi TTS application."""

import pytest
from fastapi.testclient import TestClient

from app.simple_main import app, get_service
from app.services.simple_service import SimpleTranslationTTSService


class MockService:
    """Mock service for testing."""
    
    def translate_to_hindi(self, english_text: str) -> str:
        return f"[Hindi: {english_text}]"
    
    def synthesize_speech(self, hindi_text: str) -> bytes:
        return b"fake_audio_data"
    
    @staticmethod
    def as_base64(audio_bytes: bytes) -> str:
        return SimpleTranslationTTSService.as_base64(audio_bytes)


@pytest.fixture()
def client():
    """Create test client with mocked service."""
    def get_mock_service():
        return MockService()
    
    app.dependency_overrides[get_service] = get_mock_service
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_translate_endpoint(client):
    """Test the translation endpoint."""
    payload = {"text": "Hello world"}
    response = client.post("/api/translate", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "hindi_text" in data
    assert "audio_base64" in data
    assert "audio_format" in data
    assert data["hindi_text"] == "[Hindi: Hello world]"
    assert data["audio_format"] == "wav"
    assert len(data["audio_base64"]) > 0


def test_translate_empty_text(client):
    """Test translation with empty text."""
    response = client.post("/api/translate", json={"text": ""})
    assert response.status_code == 422  # Validation error