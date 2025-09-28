"""Simple configuration for MMS TTS application."""

from dataclasses import dataclass


@dataclass
class Settings:
    """Simple settings for MMS TTS + Translation service."""
    mms_model_name: str = "facebook/mms-tts-hin"
    target_language: str = "hi"  # Hindi
    sample_rate: int = 16000


def get_settings() -> Settings:
    """Return application settings."""
    return Settings()