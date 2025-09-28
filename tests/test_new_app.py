"""Test the FastAPI application with Google Translate + MMS TTS."""

from __future__ import annotations

import base64
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app, get_translation_service
from app.services.translation_tts_service import GoogleTranslateMTTSService, TranslationTTSError


@pytest.fixture(autouse=True)
def configure_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure required env vars exist for settings loaded via dependency injection."""
    monkeypatch.setenv("MMS_MODEL_NAME", "facebook/mms-tts-hin")
    monkeypatch.setenv("TARGET_LANGUAGE", "hi")
    monkeypatch.setenv("SAMPLE_RATE", "16000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def client(configure_env: None) -> TestClient:
    return TestClient(app)


class StubTranslationService:
    def __init__(self, translation: str = "नमस्ते", audio: bytes | None = None) -> None:
        self.translation = translation
        self.audio = audio or b"fake-bytes"
        self.seen_payloads: Dict[str, Any] = {}

    def translate_to_hindi(self, text: str) -> str:
        self.seen_payloads["english"] = text
        return self.translation

    def synthesize_speech(self, hindi_text: str) -> bytes:
        self.seen_payloads["hindi"] = hindi_text
        return self.audio

    @staticmethod
    def as_base64(audio_bytes: bytes) -> str:
        return GoogleTranslateMTTSService.as_base64(audio_bytes)


@pytest.fixture()
def stub_service() -> StubTranslationService:
    return StubTranslationService()


def override_dependency(service: StubTranslationService) -> None:
    app.dependency_overrides[get_translation_service] = lambda: service


def clear_dependency_overrides() -> None:
    app.dependency_overrides.pop(get_translation_service, None)


def test_translate_success(client: TestClient, stub_service: StubTranslationService) -> None:
    override_dependency(stub_service)
    try:
        resp = client.post("/api/translate", json={"text": "Hello world"})
        assert resp.status_code == 200
        data = resp.json()
        
        assert data["hindi_text"] == "नमस्ते"
        assert data["audio_format"] == "wav"
        assert len(data["audio_base64"]) > 0
        
        # Check that the service methods were called
        assert stub_service.seen_payloads["english"] == "Hello world"
        assert stub_service.seen_payloads["hindi"] == "नमस्ते"
    finally:
        clear_dependency_overrides()


def test_health_endpoint(client: TestClient) -> None:
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_translate_empty_text(client: TestClient, stub_service: StubTranslationService) -> None:
    """Test translation with empty text."""
    override_dependency(stub_service)
    try:
        resp = client.post("/api/translate", json={"text": ""})
        assert resp.status_code == 422  # Validation error
    finally:
        clear_dependency_overrides()


def test_translate_service_failure(client: TestClient) -> None:
    """Test translation when service fails."""
    class FailingService:
        def translate_to_hindi(self, text: str) -> str:
            raise TranslationTTSError("Translation failed")
        
        def synthesize_speech(self, hindi_text: str) -> bytes:
            return b"fake"
    
    app.dependency_overrides[get_translation_service] = lambda: FailingService()
    try:
        resp = client.post("/api/translate", json={"text": "Hello"})
        assert resp.status_code == 502  # Bad Gateway
        assert "Translation failed" in resp.json()["detail"]
    finally:
        clear_dependency_overrides()