from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for Google Translate + MMS TTS service."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        frozen=True,
        extra="ignore",  # Ignore extra fields in environment
    )

    # MMS TTS Model settings
    mms_model_name: str = Field("facebook/mms-tts-hin", validation_alias="MMS_MODEL_NAME")
    target_language: str = Field("hi", validation_alias="TARGET_LANGUAGE")  # Hindi
    sample_rate: int = Field(16000, validation_alias="SAMPLE_RATE")
    request_timeout_seconds: float = Field(60.0, validation_alias="REQUEST_TIMEOUT_SECONDS")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()  # type: ignore[arg-type]
