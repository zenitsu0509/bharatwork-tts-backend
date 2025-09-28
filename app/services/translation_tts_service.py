"""Service for Google Translate + MMS TTS Hindi translation and speech synthesis."""

from __future__ import annotations

import base64
import io
import tempfile
from dataclasses import dataclass
from typing import Optional

import soundfile as sf
import torch
from deep_translator import GoogleTranslator
from transformers import VitsModel, AutoTokenizer


class TranslationTTSError(RuntimeError):
    """Raised when translation or TTS fails."""


@dataclass(slots=True)
class TranslationTTSConfig:
    """Configuration for Google Translate + MMS TTS service."""
    model_name: str = "facebook/mms-tts-hin"
    target_language: str = "hi"  # Hindi
    sample_rate: int = 16000
    request_timeout_seconds: float = 60.0


class GoogleTranslateMTTSService:
    """Service combining Google Translate and Facebook MMS TTS for Hindi."""

    def __init__(
        self,
        config: TranslationTTSConfig,
        translator: Optional[GoogleTranslator] = None,
        model: Optional[VitsModel] = None,
        tokenizer: Optional[AutoTokenizer] = None,
    ) -> None:
        self._config = config
        self._translator = translator or GoogleTranslator(source='en', target='hi')
        
        # Initialize TTS model and tokenizer
        if model is None or tokenizer is None:
            print(f"Loading MMS TTS model: {config.model_name}")
            self._model = VitsModel.from_pretrained(config.model_name)
            self._tokenizer = AutoTokenizer.from_pretrained(config.model_name)
        else:
            self._model = model
            self._tokenizer = tokenizer

    def translate_to_hindi(self, english_text: str) -> str:
        """Translate English text to Hindi using Google Translate."""
        try:
            # Clean input text
            text = english_text.strip()
            if not text:
                raise TranslationTTSError("Input text is empty")

            # Translate to Hindi using deep-translator
            result = self._translator.translate(text)
            
            if not result or not result.strip():
                raise TranslationTTSError("Google Translate returned empty result")

            return result.strip()
            
        except Exception as exc:
            raise TranslationTTSError(f"Failed to translate text: {str(exc)}") from exc

    def synthesize_speech(self, hindi_text: str) -> bytes:
        """Convert Hindi text to speech using Facebook MMS TTS."""
        try:
            # Clean input text
            text = hindi_text.strip()
            if not text:
                raise TranslationTTSError("Input text for TTS is empty")

            # Tokenize the text
            inputs = self._tokenizer(text, return_tensors="pt")
            
            # Generate audio
            with torch.no_grad():
                output = self._model(**inputs).waveform.squeeze().cpu().numpy()

            # Save to temporary file to get bytes
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                sf.write(
                    tmp_file.name, 
                    output, 
                    self._config.sample_rate,
                    format="WAV"
                )
                
                # Read the file as bytes
                with open(tmp_file.name, "rb") as audio_file:
                    audio_bytes = audio_file.read()

            return audio_bytes
            
        except Exception as exc:
            raise TranslationTTSError(f"Failed to synthesize speech: {str(exc)}") from exc

    @staticmethod
    def as_base64(audio_bytes: bytes) -> str:
        """Convert audio bytes to base64 string for frontend."""
        return base64.b64encode(audio_bytes).decode("utf-8")

    def translate_and_synthesize(self, english_text: str) -> tuple[str, bytes]:
        """Combined method to translate text and synthesize speech."""
        hindi_text = self.translate_to_hindi(english_text)
        audio_bytes = self.synthesize_speech(hindi_text)
        return hindi_text, audio_bytes