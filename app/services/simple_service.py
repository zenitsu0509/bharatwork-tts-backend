"""Simple service for English-to-Hindi translation + MMS TTS."""

import base64
import tempfile
from typing import Optional

import soundfile as sf
import torch
from deep_translator import GoogleTranslator
from transformers import VitsModel, AutoTokenizer


class TranslationTTSError(RuntimeError):
    """Raised when translation or TTS fails."""


class SimpleTranslationTTSService:
    """Simple service combining English-to-Hindi translation and MMS TTS."""

    def __init__(
        self,
        model_name: str = "facebook/mms-tts-hin",
        sample_rate: int = 16000,
        model: Optional[VitsModel] = None,
        tokenizer: Optional[AutoTokenizer] = None,
    ) -> None:
        self._model_name = model_name
        self._sample_rate = sample_rate
        
        # Initialize translator
        self._translator = GoogleTranslator(source='en', target='hi')
        
        # Initialize TTS model and tokenizer
        if model is None or tokenizer is None:
            print(f"Loading MMS TTS model: {model_name}")
            self._model = VitsModel.from_pretrained(model_name)
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        else:
            self._model = model
            self._tokenizer = tokenizer

    def translate_to_hindi(self, english_text: str) -> str:
        """Translate English text to Hindi using Google Translate."""
        try:
            text = english_text.strip()
            if not text:
                raise TranslationTTSError("Input text is empty")

            # Translate to Hindi
            result = self._translator.translate(text)
            
            if not result:
                raise TranslationTTSError("Translation returned empty result")

            return result.strip()
            
        except Exception as exc:
            raise TranslationTTSError(f"Failed to translate text: {str(exc)}") from exc

    def synthesize_speech(self, hindi_text: str) -> bytes:
        """Convert Hindi text to speech using Facebook MMS TTS."""
        try:
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
                    self._sample_rate,
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