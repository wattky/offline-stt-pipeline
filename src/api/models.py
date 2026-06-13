"""
Pydantic models for the REST API.
Designed to be compatible with OpenAI's Audio API format.
"""

from typing import Optional
from pydantic import BaseModel, Field


# --- Request Models ---

class TranscriptionRequest(BaseModel):
    """Request body for transcription (form data fields)."""
    model: str = Field(default="base", description="Model to use for transcription")
    language: Optional[str] = Field(default=None, description="Language code (e.g., 'en', 'sk')")
    prompt: Optional[str] = Field(default=None, description="Optional prompt to guide transcription")
    response_format: str = Field(default="json", description="Response format: json, text, verbose_json, srt, vtt")
    temperature: float = Field(default=0.0, description="Sampling temperature (0.0 = deterministic)")
    word_timestamps: bool = Field(default=False, description="Include word-level timestamps")


# --- Response Models ---

class TranscriptionResponse(BaseModel):
    """Standard transcription response (OpenAI-compatible)."""
    text: str


class SegmentResponse(BaseModel):
    """A single transcription segment."""
    id: int
    start: float
    end: float
    text: str
    confidence: float
    words: list = Field(default_factory=list)


class VerboseTranscriptionResponse(BaseModel):
    """Verbose transcription response with segments and metadata."""
    text: str
    language: str
    duration: float
    segments: list[SegmentResponse]


class ModelInfoResponse(BaseModel):
    """Information about a single model."""
    id: str
    name: str
    size_mb: int
    description: str
    is_downloaded: bool
    object: str = "model"


class ModelsListResponse(BaseModel):
    """List of available models."""
    object: str = "list"
    data: list[ModelInfoResponse]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    engine: dict
    uptime_seconds: float


class ErrorResponse(BaseModel):
    """Error response."""
    error: dict = Field(
        default_factory=lambda: {"message": "Unknown error", "type": "server_error", "code": 500}
    )


class DownloadProgressResponse(BaseModel):
    """Model download progress."""
    model_id: str
    status: str  # "downloading", "complete", "error"
    progress: float  # 0.0 - 100.0
    message: str


class ServerConfigResponse(BaseModel):
    """Current server configuration."""
    host: str
    port: int
    model: str
    device: str
    compute_type: str
    language: Optional[str]
    models_dir: str


class StatsResponse(BaseModel):
    """Server statistics."""
    total_requests: int
    total_audio_seconds: float
    total_processing_seconds: float
    average_rtf: float  # Real-time factor
    uptime_seconds: float
