from __future__ import annotations

import base64
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app, get_groq_service
from app.services.groq_service import GroqLLMService, GroqServiceError


@pytest.fixture(autouse=True)
def configure_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure required env vars exist for settings loaded via dependency injection."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_TTS_MODEL", "test-tts-model")
    monkeypatch.setenv("GROQ_TRANSLATION_MODEL", "test-translation-model")
    monkeypatch.setenv("GROQ_TTS_VOICE", "test-voice")
    monkeypatch.setenv("GROQ_TTS_FORMAT", "wav")
    monkeypatch.setenv("GROQ_API_BASE_URL", "https://example.com")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def client(configure_env: None) -> TestClient:
    return TestClient(app)


class StubGroqService:
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

@pytest.fixture()
def stub_service() -> StubGroqService:
    return StubGroqService()


def override_dependency(service: StubGroqService) -> None:
    app.dependency_overrides[get_groq_service] = lambda: service


def clear_dependency_overrides() -> None:
    app.dependency_overrides.pop(get_groq_service, None)


def test_translate_success(client: TestClient, stub_service: StubGroqService) -> None:
    override_dependency(stub_service)

    try:
        response = client.post("/api/translate", json={"text": "Hello"})
    finally:
        clear_dependency_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["hindi_text"] == stub_service.translation
    assert payload["audio_base64"] == base64.b64encode(stub_service.audio).decode()
    assert payload["audio_format"] == "wav"
    assert stub_service.seen_payloads == {"english": "Hello", "hindi": stub_service.translation}


def test_translate_handles_service_error(client: TestClient) -> None:
    class ErrorService(StubGroqService):
        def translate_to_hindi(self, text: str) -> str:
            raise GroqServiceError("Translation failed")

    override_dependency(ErrorService())

    try:
        response = client.post("/api/translate", json={"text": "Hello"})
    finally:
        clear_dependency_overrides()

    assert response.status_code == 502
    assert response.json()["detail"] == "Translation failed"


def test_translate_validates_input(client: TestClient) -> None:
    response = client.post("/api/translate", json={"text": ""})
    assert response.status_code == 422


def test_healthcheck(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
