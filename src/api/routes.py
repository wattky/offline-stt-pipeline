"""
FastAPI routes for the Offline STT Pipeline.
Provides OpenAI-compatible endpoints for speech-to-text transcription.
"""

import os
import time
import logging
import tempfile
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse

from .models import (
    TranscriptionResponse,
    VerboseTranscriptionResponse,
    SegmentResponse,
    ModelInfoResponse,
    ModelsListResponse,
    HealthResponse,
    ErrorResponse,
    ServerConfigResponse,
    StatsResponse,
)
from ..engine.whisper import WhisperEngine
from ..engine.downloader import ModelDownloader
from ..utils.config import ConfigManager, AVAILABLE_MODELS, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

# Global state
_engine: Optional[WhisperEngine] = None
_downloader: Optional[ModelDownloader] = None
_config: Optional[ConfigManager] = None
_start_time: float = 0
_stats = {
    "total_requests": 0,
    "total_audio_seconds": 0.0,
    "total_processing_seconds": 0.0,
}

VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global _engine, _downloader, _config, _start_time
    
    _start_time = time.time()
    _config = ConfigManager()
    _downloader = ModelDownloader(_config.config.models_dir)
    
    # Initialize engine
    _engine = WhisperEngine(
        model_size_or_path=_config.config.engine.model_size,
        device=_config.config.engine.device,
        compute_type=_config.config.engine.compute_type,
        models_dir=_config.config.models_dir,
    )
    
    # Try to load model if available
    if _downloader.is_model_downloaded(_config.config.engine.model_size):
        try:
            _engine.load_model()
            logger.info(f"Model '{_config.config.engine.model_size}' loaded at startup")
        except Exception as e:
            logger.warning(f"Could not load model at startup: {e}")
    else:
        logger.info(
            f"Model '{_config.config.engine.model_size}' not downloaded. "
            "Use /v1/models/download to download a model."
        )
    
    yield
    
    # Cleanup
    if _engine:
        _engine.unload_model()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Offline STT Pipeline",
        description=(
            "Cross-platform offline Speech-to-Text API server. "
            "OpenAI-compatible endpoint for Voice AI integration."
        ),
        version=VERSION,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Health & Info Endpoints ---

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health_check():
        """Check server health and status."""
        return HealthResponse(
            status="ready" if _engine and _engine.is_loaded else "no_model",
            version=VERSION,
            engine=_engine.get_info() if _engine else {},
            uptime_seconds=round(time.time() - _start_time, 1),
        )

    @app.get("/v1/stats", response_model=StatsResponse, tags=["System"])
    async def get_stats():
        """Get server statistics."""
        avg_rtf = 0.0
        if _stats["total_audio_seconds"] > 0:
            avg_rtf = _stats["total_processing_seconds"] / _stats["total_audio_seconds"]
        
        return StatsResponse(
            total_requests=_stats["total_requests"],
            total_audio_seconds=round(_stats["total_audio_seconds"], 1),
            total_processing_seconds=round(_stats["total_processing_seconds"], 1),
            average_rtf=round(avg_rtf, 3),
            uptime_seconds=round(time.time() - _start_time, 1),
        )

    @app.get("/v1/config", response_model=ServerConfigResponse, tags=["System"])
    async def get_config():
        """Get current server configuration."""
        return ServerConfigResponse(
            host=_config.config.server.host,
            port=_config.config.server.port,
            model=_config.config.engine.model_size,
            device=_engine.device if _engine else "unknown",
            compute_type=_engine.compute_type if _engine else "unknown",
            language=_config.config.engine.language,
            models_dir=_config.config.models_dir,
        )

    @app.get("/v1/languages", tags=["System"])
    async def get_languages():
        """Get list of supported languages."""
        return {"languages": SUPPORTED_LANGUAGES}

    # --- Model Management Endpoints ---

    @app.get("/v1/models", response_model=ModelsListResponse, tags=["Models"])
    async def list_models():
        """List all available models and their download status."""
        models = _downloader.list_models()
        return ModelsListResponse(
            data=[
                ModelInfoResponse(
                    id=m.model_id,
                    name=m.name,
                    size_mb=m.size_mb,
                    description=m.description,
                    is_downloaded=m.is_downloaded,
                )
                for m in models
            ]
        )

    @app.post("/v1/models/download/{model_id}", tags=["Models"])
    async def download_model(model_id: str):
        """Download a model for offline use."""
        if model_id not in AVAILABLE_MODELS:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown model: {model_id}. Available: {list(AVAILABLE_MODELS.keys())}",
            )
        
        if _downloader.is_model_downloaded(model_id):
            return {"status": "already_downloaded", "model_id": model_id}
        
        try:
            _downloader.download_model(model_id)
            return {"status": "complete", "model_id": model_id}
        except ConnectionError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/v1/models/{model_id}", tags=["Models"])
    async def delete_model(model_id: str):
        """Delete a downloaded model."""
        if _downloader.delete_model(model_id):
            return {"status": "deleted", "model_id": model_id}
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    @app.post("/v1/models/load/{model_id}", tags=["Models"])
    async def load_model(model_id: str):
        """Load a specific model into memory."""
        global _engine
        
        if not _downloader.is_model_downloaded(model_id):
            raise HTTPException(
                status_code=404,
                detail=f"Model {model_id} is not downloaded. Download it first.",
            )
        
        # Unload current model
        if _engine:
            _engine.unload_model()
        
        # Load new model
        _engine = WhisperEngine(
            model_size_or_path=model_id,
            device=_config.config.engine.device,
            compute_type=_config.config.engine.compute_type,
            models_dir=_config.config.models_dir,
        )
        
        if _engine.load_model():
            _config.update_engine(model_size=model_id)
            return {"status": "loaded", "model_id": model_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to load model")

    # --- Transcription Endpoints (OpenAI-compatible) ---

    @app.post("/v1/audio/transcriptions", tags=["Transcription"])
    async def transcribe_audio(
        file: UploadFile = File(..., description="Audio file to transcribe"),
        model: str = Form(default="base", description="Model to use"),
        language: Optional[str] = Form(default=None, description="Language code"),
        prompt: Optional[str] = Form(default=None, description="Optional prompt"),
        response_format: str = Form(default="json", description="Response format"),
        temperature: float = Form(default=0.0, description="Temperature"),
        word_timestamps: bool = Form(default=False, description="Word timestamps"),
    ):
        """
        Transcribe audio file to text.
        
        OpenAI-compatible endpoint. Accepts audio files in various formats
        (wav, mp3, m4a, flac, ogg, webm) and returns transcribed text.
        
        This is the main endpoint for Voice AI pipeline integration.
        """
        if not _engine or not _engine.is_loaded:
            raise HTTPException(
                status_code=503,
                detail="No model loaded. Download and load a model first.",
            )

        # Read uploaded file
        try:
            audio_bytes = await file.read()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read audio file: {e}")

        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")

        # Save to temp file (faster-whisper needs a file path for non-WAV formats)
        suffix = Path(file.filename).suffix if file.filename else ".wav"
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            # Transcribe
            result = _engine.transcribe(
                audio_data=tmp_path,
                language=language,
                beam_size=5,
                vad_filter=True,
                word_timestamps=word_timestamps,
                initial_prompt=prompt,
            )

            # Update stats
            _stats["total_requests"] += 1
            _stats["total_audio_seconds"] += result.duration
            _stats["total_processing_seconds"] += result.processing_time

            # Format response based on requested format
            if response_format == "text":
                return PlainTextResponse(content=result.text)
            
            elif response_format == "srt":
                srt_content = _format_srt(result.segments)
                return PlainTextResponse(content=srt_content, media_type="text/plain")
            
            elif response_format == "vtt":
                vtt_content = _format_vtt(result.segments)
                return PlainTextResponse(content=vtt_content, media_type="text/vtt")
            
            elif response_format == "verbose_json":
                return VerboseTranscriptionResponse(
                    text=result.text,
                    language=result.language,
                    duration=result.duration,
                    segments=[
                        SegmentResponse(
                            id=s.id,
                            start=s.start,
                            end=s.end,
                            text=s.text,
                            confidence=s.confidence,
                            words=s.words,
                        )
                        for s in result.segments
                    ],
                )
            
            else:  # json (default, OpenAI-compatible)
                return TranscriptionResponse(text=result.text)

        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            # Clean up temp file
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # --- UI Endpoint ---

    @app.get("/", response_class=HTMLResponse, tags=["UI"])
    async def serve_ui():
        """Serve the web UI."""
        ui_path = Path(__file__).parent.parent / "ui" / "templates" / "index.html"
        if ui_path.exists():
            return HTMLResponse(content=ui_path.read_text())
        return HTMLResponse(
            content="<h1>Offline STT Pipeline</h1><p>UI not found. API is running at /docs</p>"
        )

    # Mount static files
    static_path = Path(__file__).parent.parent / "ui" / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    return app


def _format_srt(segments) -> str:
    """Format segments as SRT subtitle format."""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _format_timestamp_srt(seg.start)
        end = _format_timestamp_srt(seg.end)
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(seg.text)
        lines.append("")
    return "\n".join(lines)


def _format_vtt(segments) -> str:
    """Format segments as WebVTT subtitle format."""
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = _format_timestamp_vtt(seg.start)
        end = _format_timestamp_vtt(seg.end)
        lines.append(f"{start} --> {end}")
        lines.append(seg.text)
        lines.append("")
    return "\n".join(lines)


def _format_timestamp_srt(seconds: float) -> str:
    """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_timestamp_vtt(seconds: float) -> str:
    """Format seconds as VTT timestamp (HH:MM:SS.mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
