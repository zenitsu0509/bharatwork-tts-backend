# BharatWork TTS Backend

A minimal FastAPI backend with a simple HTML frontend that uses Groq-hosted LLMs to translate English sentences into Hindi and render the Hindi text as speech.

## Features

- 🌐 REST API built with FastAPI (`/api/translate`) and a health probe (`/health`).
- 🧠 Translation using a Groq chat completion model (default: `llama-3.1-8b-instant`).
- 🔊 Text-to-speech via Groq's audio synthesis endpoint (default model: `playai-tts`, voice `Aaliyah-PlayAI`, WAV output).
- 🎨 Lightweight HTML/CSS frontend served from `app/templates/index.html` with vanilla JS for interactions.
- ✅ Automated tests with `pytest` verifying happy path, error propagation, and validation.

> **Note:** Groq's API surface is evolving. The defaults in this project assume the OpenAI-compatible endpoints exposed at `https://api.groq.com/openai/v1`. Update model names if your account uses different identifiers.

## Getting started

### 1. Clone & set up a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and populate your Groq credentials:

```bash
# macOS/Linux
cp .env.example .env
# Windows (PowerShell)
copy .env.example .env
# edit .env and set GROQ_API_KEY
```

At a minimum you must provide `GROQ_API_KEY`. All other values have sensible defaults and can be left as-is unless you prefer different Groq models/voices.

### 3. Run the development server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser, type an English sentence, and click **Translate & Speak**. The Hindi translation and playable audio will appear beneath the form.

### 4. Run the test suite

```bash
pytest
```

Tests mock the Groq service so they run offline and without your API key.

## Project structure

```text
app/
  main.py              # FastAPI application entrypoint and routes
  config.py            # Pydantic settings wrapper for environment variables
  services/
    groq_service.py    # Translation + TTS helper built on Groq APIs
  templates/index.html # Frontend page
  static/
    styles.css         # Styling for the UI
    script.js          # Browser logic, form handling, audio playback
.tests/
  test_app.py          # Pytest coverage for API routes
requirements.txt        # Python dependencies
.env.example            # Template for required environment variables
README.md               # This documentation
```

## API reference

### `POST /api/translate`

#### Request body

```json
{
  "text": "Hello there"
}
```

#### Successful response

```json
{
  "hindi_text": "नमस्ते",
  "audio_base64": "<base64-encoded wav bytes>",
  "audio_format": "wav"
}
```

The frontend decodes `audio_base64` into an `audio/<format>` blob for playback.

## Customization tips

- **Swap models / voices:** Set `GROQ_TRANSLATION_MODEL`, `GROQ_TTS_MODEL`, or `GROQ_TTS_VOICE` in your `.env` file.
- **Change audio format:** Update `GROQ_TTS_FORMAT` to a format supported by the Groq TTS model (e.g., `mp3`). The frontend adapts automatically.
- **Provider-specific voices:** Supply `GROQ_TTS_PROVIDER` (e.g., `PlayAI`) or append the provider name to the voice (e.g., `Aaliyah-PlayAI`) and the service will shape the payload accordingly.
- **Reuse the API:** `app.services.groq_service.GroqLLMService` can be injected elsewhere in the codebase for additional workflows.

## Troubleshooting

- **`422 Unprocessable Entity`** – The request body is missing the `text` field or it's empty.
- **`502 Bad Gateway`** – Groq returned an error or timed out. Check your API key, quota, model/voice names, or provider. The backend now surfaces Groq's status code and message to help spot misconfigurations.
- **CORS issues** – Adjust `allow_origins` in `app.main` if serving the frontend from a different host.

Happy building! 🇮🇳🗣️
