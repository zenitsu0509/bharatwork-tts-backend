"""Simple FastAPI application for English-to-Hindi translation + TTS."""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.services.simple_service import SimpleTranslationTTSService, TranslationTTSError
from app.simple_config import Settings, get_settings

logger = logging.getLogger(__name__)

app = FastAPI(title="Simple English-to-Hindi TTS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


class TranslationRequest(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=2_000)]


class TranslationResponse(BaseModel):
    hindi_text: str
    audio_base64: str
    audio_format: str


def build_service(settings: Settings) -> SimpleTranslationTTSService:
    return SimpleTranslationTTSService(
        model_name=settings.mms_model_name,
        sample_rate=settings.sample_rate,
    )


def get_service(settings: Annotated[Settings, Depends(get_settings)]) -> SimpleTranslationTTSService:
    return build_service(settings)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/translate", response_model=TranslationResponse)
async def translate(
    payload: TranslationRequest,
    service: Annotated[SimpleTranslationTTSService, Depends(get_service)],
) -> TranslationResponse:
    try:
        hindi_text = await run_in_threadpool(service.translate_to_hindi, payload.text)
        audio_bytes = await run_in_threadpool(service.synthesize_speech, hindi_text)
    except TranslationTTSError as exc:
        logger.exception("Translation/TTS service failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    audio_base64 = SimpleTranslationTTSService.as_base64(audio_bytes)
    return TranslationResponse(
        hindi_text=hindi_text,
        audio_base64=audio_base64,
        audio_format="wav",
    )