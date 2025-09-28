from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.groq_service import GroqLLMService, GroqServiceConfig


@pytest.fixture()
def dummy_client() -> SimpleNamespace:
    # Minimal object to satisfy GroqLLMService without performing network calls.
    return SimpleNamespace()


def test_synthesize_speech_supports_playai_provider(monkeypatch: pytest.MonkeyPatch, dummy_client: SimpleNamespace) -> None:
    captured: dict[str, object] = {}

    class DummyResponse:
        status_code = 200
        content = b"abc"

        def raise_for_status(self) -> None:  # noqa: D401 - mimic httpx.Response API
            """No-op."""

    def fake_post(url: str, json: dict[str, object], headers: dict[str, str], timeout: float) -> DummyResponse:
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("app.services.groq_service.httpx.post", fake_post)

    config = GroqServiceConfig(
        api_key="test-key",
        translation_model="translator",
        tts_model="playai-tts",
        tts_voice="Aaliyah-PlayAI",
        tts_format="wav",
        api_base_url="https://api.groq.com/openai/v1",
    )
    service = GroqLLMService(config=config, client=dummy_client)

    audio = service.synthesize_speech("नमस्ते")

    assert audio == b"abc"
    payload = captured["json"]
    assert payload["model"] == "playai-tts"
    assert payload["voice"] == "Aaliyah"
    assert payload["provider"] == "PlayAI"
    assert payload["format"] == "wav"
    assert captured["headers"]["Accept"] == "audio/wav"
    assert captured["url"] == "https://api.groq.com/openai/v1/audio/speech"
```}