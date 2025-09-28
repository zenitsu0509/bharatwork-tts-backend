"""Bulk audio generation service with modular audio components."""

from __future__ import annotations

import base64
import io
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import logging

import pandas as pd
import soundfile as sf
import torch
import numpy as np
from scipy.io import wavfile
from transformers import VitsModel, AutoTokenizer
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)


class BulkAudioError(RuntimeError):
    """Raised when bulk audio generation fails."""


@dataclass
class AudioTemplate:
    """Represents a reusable audio template."""
    text: str
    audio_path: str
    duration_ms: int


@dataclass
class CallData:
    """Represents data for a single call."""
    name: str
    company_name: str
    salary: str
    phone_number: str


class BulkAudioService:
    """Service for generating bulk audio with reusable components."""

    def __init__(self, model_name: str = "facebook/mms-tts-hin", sample_rate: int = 16000):
        self.model_name = model_name
        self.sample_rate = sample_rate
        self.translator = GoogleTranslator(source='en', target='hi')
        
        # Initialize TTS model
        logger.info(f"Loading MMS TTS model: {model_name}")
        self.model = VitsModel.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Create templates directory
        self.templates_dir = Path("audio_templates")
        self.templates_dir.mkdir(exist_ok=True)
        
        # Master templates for common phrases
        self.master_templates = {
            "greeting": "Hello",
            "intro": "this is a call from BharatWork",
            "opportunity": "We have an excellent job opportunity for you",
            "company_intro": "The position is with",
            "salary_intro": "The offered salary is",
            "contact_info": "For more details, please contact us at",
            "closing": "Thank you for your time"
        }
        
        self._generated_templates: Dict[str, AudioTemplate] = {}

    def _text_to_audio_bytes(self, text: str) -> bytes:
        """Convert text to audio bytes using MMS TTS."""
        try:
            # Tokenize the text
            inputs = self.tokenizer(text, return_tensors="pt")
            
            # Generate audio
            with torch.no_grad():
                output = self.model(**inputs).waveform.squeeze().cpu().numpy()

            # Convert to bytes using in-memory buffer
            buffer = io.BytesIO()
            sf.write(buffer, output, self.sample_rate, format="WAV")
            audio_bytes = buffer.getvalue()
            buffer.close()
            
            return audio_bytes
            
        except Exception as exc:
            raise BulkAudioError(f"Failed to synthesize speech for '{text}': {str(exc)}") from exc

    def _save_audio_template(self, key: str, text: str) -> AudioTemplate:
        """Generate and save an audio template."""
        try:
            # Translate to Hindi if needed
            hindi_text = self.translator.translate(text)
            
            # Generate audio
            audio_bytes = self._text_to_audio_bytes(hindi_text)
            
            # Save to file
            template_path = self.templates_dir / f"{key}.wav"
            with open(template_path, "wb") as f:
                f.write(audio_bytes)
            
            # Get duration using soundfile
            audio_data, sample_rate = sf.read(template_path)
            duration_ms = int((len(audio_data) / sample_rate) * 1000)
            
            template = AudioTemplate(
                text=hindi_text,
                audio_path=str(template_path),
                duration_ms=duration_ms
            )
            
            logger.info(f"Generated template '{key}': {hindi_text} ({duration_ms}ms)")
            return template
            
        except Exception as exc:
            raise BulkAudioError(f"Failed to create template for '{text}': {str(exc)}") from exc

    def generate_master_templates(self) -> Dict[str, AudioTemplate]:
        """Generate all master audio templates."""
        logger.info("Generating master audio templates...")
        
        for key, text in self.master_templates.items():
            if key not in self._generated_templates:
                template = self._save_audio_template(key, text)
                self._generated_templates[key] = template
        
        logger.info(f"Generated {len(self._generated_templates)} master templates")
        return self._generated_templates.copy()

    def generate_variable_audio(self, text: str) -> bytes:
        """Generate audio for variable text (names, companies, etc.)."""
        try:
            # Translate to Hindi
            hindi_text = self.translator.translate(text)
            
            # Generate audio
            audio_bytes = self._text_to_audio_bytes(hindi_text)
            
            return audio_bytes
            
        except Exception as exc:
            raise BulkAudioError(f"Failed to generate variable audio for '{text}': {str(exc)}") from exc

    def merge_audio_components(self, call_data: CallData) -> bytes:
        """Merge audio components to create a complete call audio."""
        try:
            # Ensure templates exist
            if not self._generated_templates:
                self.generate_master_templates()
            
            # Create audio segments list
            audio_segments = []
            
            # Helper function to load audio as numpy array
            def load_audio_data(file_path: str) -> np.ndarray:
                audio_data, _ = sf.read(file_path)
                return audio_data
            
            # Helper function to save audio bytes to temp file and load as numpy array
            def bytes_to_audio_data(audio_bytes: bytes) -> np.ndarray:
                buffer = io.BytesIO(audio_bytes)
                audio_data, _ = sf.read(buffer)
                buffer.close()
                return audio_data
            
            # 1. "Hello"
            greeting_audio = load_audio_data(self._generated_templates["greeting"].audio_path)
            audio_segments.append(greeting_audio)
            
            # 2. Name (generate dynamically)
            name_audio_bytes = self.generate_variable_audio(call_data.name)
            name_audio = bytes_to_audio_data(name_audio_bytes)
            audio_segments.append(name_audio)
            
            # 3. "this is a call from BharatWork"
            intro_audio = load_audio_data(self._generated_templates["intro"].audio_path)
            audio_segments.append(intro_audio)
            
            # 4. "We have an excellent job opportunity for you"
            opportunity_audio = load_audio_data(self._generated_templates["opportunity"].audio_path)
            audio_segments.append(opportunity_audio)
            
            # 5. "The position is with"
            company_intro_audio = load_audio_data(self._generated_templates["company_intro"].audio_path)
            audio_segments.append(company_intro_audio)
            
            # 6. Company name (generate dynamically)
            company_audio_bytes = self.generate_variable_audio(call_data.company_name)
            company_audio = bytes_to_audio_data(company_audio_bytes)
            audio_segments.append(company_audio)
            
            # 7. "The offered salary is"
            salary_intro_audio = load_audio_data(self._generated_templates["salary_intro"].audio_path)
            audio_segments.append(salary_intro_audio)
            
            # 8. Salary (generate dynamically)
            salary_audio_bytes = self.generate_variable_audio(call_data.salary)
            salary_audio = bytes_to_audio_data(salary_audio_bytes)
            audio_segments.append(salary_audio)
            
            # 9. "For more details, please contact us at"
            contact_info_audio = load_audio_data(self._generated_templates["contact_info"].audio_path)
            audio_segments.append(contact_info_audio)
            
            # 10. Phone number (generate dynamically)
            phone_audio_bytes = self.generate_variable_audio(call_data.phone_number)
            phone_audio = bytes_to_audio_data(phone_audio_bytes)
            audio_segments.append(phone_audio)
            
            # 11. "Thank you for your time"
            closing_audio = load_audio_data(self._generated_templates["closing"].audio_path)
            audio_segments.append(closing_audio)
            
            # Create silence padding (300ms at 16kHz)
            silence_samples = int(0.3 * self.sample_rate)
            silence = np.zeros(silence_samples)
            
            # Merge all segments with pauses
            merged_audio = np.array([])
            
            for i, segment in enumerate(audio_segments):
                merged_audio = np.concatenate([merged_audio, segment])
                if i < len(audio_segments) - 1:  # Don't add pause after last segment
                    merged_audio = np.concatenate([merged_audio, silence])
            
            # Save merged audio to bytes
            buffer = io.BytesIO()
            sf.write(buffer, merged_audio, self.sample_rate, format="WAV")
            merged_bytes = buffer.getvalue()
            buffer.close()
            
            logger.info(f"Generated merged audio for {call_data.name} ({len(merged_bytes)} bytes)")
            return merged_bytes
            
        except Exception as exc:
            raise BulkAudioError(f"Failed to merge audio for {call_data.name}: {str(exc)}") from exc

    def process_csv_data(self, csv_content: str) -> List[CallData]:
        """Process CSV content and return list of call data."""
        try:
            # Read CSV
            df = pd.read_csv(io.StringIO(csv_content))
            
            # Expected columns
            required_columns = ['name', 'company_name', 'salary', 'phone_number']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise BulkAudioError(f"Missing required columns: {missing_columns}")
            
            # Convert to CallData objects
            call_data_list = []
            for _, row in df.iterrows():
                call_data = CallData(
                    name=str(row['name']).strip(),
                    company_name=str(row['company_name']).strip(),
                    salary=str(row['salary']).strip(),
                    phone_number=str(row['phone_number']).strip()
                )
                call_data_list.append(call_data)
            
            logger.info(f"Processed {len(call_data_list)} records from CSV")
            return call_data_list
            
        except Exception as exc:
            raise BulkAudioError(f"Failed to process CSV data: {str(exc)}") from exc

    @staticmethod
    def audio_to_base64(audio_bytes: bytes) -> str:
        """Convert audio bytes to base64 string."""
        return base64.b64encode(audio_bytes).decode("utf-8")