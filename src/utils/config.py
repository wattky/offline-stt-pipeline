"""
Configuration management for Offline STT Pipeline.
Handles application settings, model paths, and server configuration.
"""

import os
import json
import platform
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


def get_app_data_dir() -> Path:
    """Get the platform-specific application data directory."""
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    
    app_dir = base / "offline-stt-pipeline"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_models_dir() -> Path:
    """Get the directory where models are stored."""
    models_dir = get_app_data_dir() / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


@dataclass
class ServerConfig:
    """Server configuration settings."""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    cors_origins: list = field(default_factory=lambda: ["*"])


@dataclass
class EngineConfig:
    """STT Engine configuration settings."""
    model_size: str = "base"
    device: str = "auto"  # "auto", "cpu", "cuda"
    compute_type: str = "auto"  # "auto", "int8", "float16", "float32"
    language: Optional[str] = None  # None = auto-detect
    beam_size: int = 5
    vad_filter: bool = True
    vad_threshold: float = 0.5


@dataclass
class AppConfig:
    """Main application configuration."""
    server: ServerConfig = field(default_factory=ServerConfig)
    engine: EngineConfig = field(default_factory=EngineConfig)
    models_dir: str = ""
    first_run: bool = True

    def __post_init__(self):
        if not self.models_dir:
            self.models_dir = str(get_models_dir())


# Available Whisper models with metadata
AVAILABLE_MODELS = {
    "tiny": {
        "name": "Tiny",
        "size_mb": 75,
        "description": "Fastest, lowest accuracy. Good for quick testing.",
        "url": "https://huggingface.co/Systran/faster-whisper-tiny",
    },
    "base": {
        "name": "Base",
        "size_mb": 142,
        "description": "Balanced speed and accuracy. Recommended for most use cases.",
        "url": "https://huggingface.co/Systran/faster-whisper-base",
    },
    "small": {
        "name": "Small",
        "size_mb": 466,
        "description": "Good accuracy with moderate speed.",
        "url": "https://huggingface.co/Systran/faster-whisper-small",
    },
    "medium": {
        "name": "Medium",
        "size_mb": 1500,
        "description": "High accuracy, slower processing.",
        "url": "https://huggingface.co/Systran/faster-whisper-medium",
    },
    "large-v3": {
        "name": "Large V3",
        "size_mb": 3000,
        "description": "Highest accuracy, requires significant resources.",
        "url": "https://huggingface.co/Systran/faster-whisper-large-v3",
    },
}

# Supported languages (subset for UI display)
SUPPORTED_LANGUAGES = {
    "auto": "Auto-detect",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "pl": "Polish",
    "ru": "Russian",
    "uk": "Ukrainian",
    "cs": "Czech",
    "sk": "Slovak",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ar": "Arabic",
    "hi": "Hindi",
    "tr": "Turkish",
    "sv": "Swedish",
    "da": "Danish",
    "fi": "Finnish",
    "no": "Norwegian",
    "hu": "Hungarian",
    "ro": "Romanian",
    "bg": "Bulgarian",
    "hr": "Croatian",
    "sl": "Slovenian",
    "he": "Hebrew",
    "th": "Thai",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "ms": "Malay",
}


class ConfigManager:
    """Manages loading and saving application configuration."""

    def __init__(self):
        self.config_path = get_app_data_dir() / "config.json"
        self.config = self._load()

    def _load(self) -> AppConfig:
        """Load configuration from disk or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                server = ServerConfig(**data.get("server", {}))
                engine = EngineConfig(**data.get("engine", {}))
                return AppConfig(
                    server=server,
                    engine=engine,
                    models_dir=data.get("models_dir", ""),
                    first_run=data.get("first_run", True),
                )
            except (json.JSONDecodeError, TypeError, KeyError):
                pass
        return AppConfig()

    def save(self):
        """Save current configuration to disk."""
        data = asdict(self.config)
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=2)

    def update_engine(self, **kwargs):
        """Update engine configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config.engine, key):
                setattr(self.config.engine, key, value)
        self.save()

    def update_server(self, **kwargs):
        """Update server configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config.server, key):
                setattr(self.config.server, key, value)
        self.save()
