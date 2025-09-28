
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Annotated, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from config import Settings, get_settings
from services.translation_tts_service import (
    GoogleTranslateMTTSService, 
    TranslationTTSConfig, 
    TranslationTTSError
)
from services.bulk_audio_service import BulkAudioService, BulkAudioError, CallData

logger = logging.getLogger(__name__)


app = FastAPI(title="BharatWork TTS Backend - Bulk Audio Generation")

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

class CSVPathRequest(BaseModel):
    csv_path: str
    output_folder: Optional[str] = None

class BulkGenerationPathRequest(BaseModel):
    csv_path: str
    selected_indices: Optional[List[int]] = None  # Specific record indices to generate
    output_folder: Optional[str] = None

def build_translation_service(settings: Settings) -> GoogleTranslateMTTSService:
    config = TranslationTTSConfig(
        model_name=settings.mms_model_name,
        target_language=settings.target_language,
        sample_rate=settings.sample_rate,
        request_timeout_seconds=settings.request_timeout_seconds,
    )
    return GoogleTranslateMTTSService(config)

def get_translation_service(settings: Annotated[Settings, Depends(get_settings)]) -> GoogleTranslateMTTSService:
    return build_translation_service(settings)

def get_bulk_audio_service() -> BulkAudioService:
    return BulkAudioService()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/bulk-path", response_class=HTMLResponse)
async def bulk_audio_path(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("bulk_path.html", {"request": request})

@app.post("/api/translate", response_model=TranslationResponse)
async def translate(
    payload: TranslationRequest,
    service: Annotated[GoogleTranslateMTTSService, Depends(get_translation_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TranslationResponse:
    try:
        hindi_text = await run_in_threadpool(service.translate_to_hindi, payload.text)
        audio_bytes = await run_in_threadpool(service.synthesize_speech, hindi_text)
    except TranslationTTSError as exc:
        logger.exception("Translation/TTS service failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    audio_base64 = GoogleTranslateMTTSService.as_base64(audio_bytes)
    return TranslationResponse(
        hindi_text=hindi_text,
        audio_base64=audio_base64,
        audio_format="wav",
    )

@app.post("/api/process-csv-path")
async def process_csv_path(
    payload: CSVPathRequest,
    bulk_service: Annotated[BulkAudioService, Depends(get_bulk_audio_service)],
):
    """Process CSV file from path and return parsed call data."""
    try:
        # Check if file exists
        if not os.path.exists(payload.csv_path):
            raise HTTPException(status_code=400, detail="CSV file not found")
        
        if not payload.csv_path.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        # Read CSV file
        with open(payload.csv_path, 'r', encoding='utf-8') as file:
            csv_content = file.read()
        
        call_data_list = await run_in_threadpool(bulk_service.process_csv_data, csv_content)
        
        return {
            "message": f"Successfully processed {len(call_data_list)} records",
            "records": len(call_data_list),
            "preview": [
                {
                    "index": i,
                    "name": cd.name,
                    "company_name": cd.company_name,
                    "salary": cd.salary,
                    "phone_number": cd.phone_number
                } for i, cd in enumerate(call_data_list[:10])  # Show first 10 records with index
            ]
        }
    except BulkAudioError as exc:
        logger.exception("CSV processing failed")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error processing CSV")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

@app.post("/api/generate-bulk-audio-path")
async def generate_bulk_audio_path(
    payload: BulkGenerationPathRequest,
    bulk_service: Annotated[BulkAudioService, Depends(get_bulk_audio_service)],
):
    """Generate audio files for selected records from CSV file path."""
    try:
        # Check if file exists
        if not os.path.exists(payload.csv_path):
            raise HTTPException(status_code=400, detail="CSV file not found")
        
        if not payload.csv_path.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        # Read CSV file
        with open(payload.csv_path, 'r', encoding='utf-8') as file:
            csv_content = file.read()
        
        # Process CSV
        call_data_list = await run_in_threadpool(bulk_service.process_csv_data, csv_content)
        
        # Filter records if specific indices are selected
        if payload.selected_indices:
            call_data_list = [call_data_list[i] for i in payload.selected_indices if i < len(call_data_list)]
        
        # Generate audio files
        audio_files = []
        saved_files = []
        
        for i, call_data in enumerate(call_data_list):
            audio_bytes = await run_in_threadpool(bulk_service.merge_audio_components, call_data)
            
            # Save to output folder if specified
            if payload.output_folder:
                os.makedirs(payload.output_folder, exist_ok=True)
                output_filename = f"{call_data.name.replace(' ', '_')}_{call_data.company_name.replace(' ', '_')}.wav"
                output_path = os.path.join(payload.output_folder, output_filename)
                
                with open(output_path, 'wb') as f:
                    f.write(audio_bytes)
                
                saved_files.append({
                    "name": call_data.name,
                    "company_name": call_data.company_name,
                    "file_path": output_path
                })
            else:
                # Return as base64 if no output folder
                audio_base64 = BulkAudioService.audio_to_base64(audio_bytes)
                audio_files.append({
                    "name": call_data.name,
                    "company_name": call_data.company_name,
                    "audio_base64": audio_base64
                })
        
        response_data = {
            "total_generated": len(call_data_list),
            "message": f"Successfully generated {len(call_data_list)} audio files"
        }
        
        if payload.output_folder:
            response_data["saved_files"] = saved_files
            response_data["output_folder"] = payload.output_folder
        else:
            response_data["audio_files"] = audio_files
        
        return response_data
        
    except BulkAudioError as exc:
        logger.exception("Bulk audio generation failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error generating bulk audio")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting BharatWork TTS Backend - Bulk Audio Generation")
    print("📝 Server will be available at: http://localhost:8000")
    print("🎵 Bulk Audio Interface: http://localhost:8000/bulk-path")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("-" * 60)
    
    uvicorn.run(
        "main_bulk:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )