"""
Model Downloader for Offline STT Pipeline.
Handles downloading, verifying, and managing Whisper models.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

from ..utils.config import AVAILABLE_MODELS, get_models_dir

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Information about a downloaded model."""
    model_id: str
    name: str
    size_mb: int
    path: str
    is_downloaded: bool
    description: str


class ModelDownloader:
    """Manages downloading and storage of Whisper models."""

    def __init__(self, models_dir: Optional[str] = None):
        self.models_dir = Path(models_dir) if models_dir else get_models_dir()
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def list_models(self) -> list[ModelInfo]:
        """List all available models with their download status."""
        models = []
        for model_id, meta in AVAILABLE_MODELS.items():
            model_path = self.models_dir / model_id
            is_downloaded = model_path.exists() and any(model_path.iterdir()) if model_path.exists() else False
            models.append(ModelInfo(
                model_id=model_id,
                name=meta["name"],
                size_mb=meta["size_mb"],
                path=str(model_path),
                is_downloaded=is_downloaded,
                description=meta["description"],
            ))
        return models

    def get_model_path(self, model_id: str) -> Optional[Path]:
        """Get the path to a downloaded model, or None if not downloaded."""
        if model_id not in AVAILABLE_MODELS:
            return None
        model_path = self.models_dir / model_id
        if model_path.exists() and any(model_path.iterdir()):
            return model_path
        return None

    def is_model_downloaded(self, model_id: str) -> bool:
        """Check if a model is already downloaded."""
        return self.get_model_path(model_id) is not None

    def download_model(
        self,
        model_id: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Path:
        """
        Download a model from HuggingFace.
        
        Uses the faster-whisper download utility which handles caching
        and verification automatically.
        
        Args:
            model_id: The model identifier (e.g., "base", "small")
            progress_callback: Optional callback(progress_pct, status_msg)
            
        Returns:
            Path to the downloaded model directory
            
        Raises:
            ValueError: If model_id is not valid
            ConnectionError: If download fails (no internet)
            RuntimeError: If download fails for other reasons
        """
        if model_id not in AVAILABLE_MODELS:
            raise ValueError(
                f"Unknown model: {model_id}. "
                f"Available: {list(AVAILABLE_MODELS.keys())}"
            )

        model_path = self.models_dir / model_id

        if progress_callback:
            progress_callback(0.0, f"Starting download of {model_id} model...")

        try:
            # Use faster-whisper's built-in download mechanism
            from faster_whisper.utils import download_model

            if progress_callback:
                progress_callback(10.0, "Downloading from HuggingFace...")

            # Download to our models directory
            output_dir = str(model_path)
            download_model(
                size_or_id=f"Systran/faster-whisper-{model_id}",
                output_dir=output_dir,
            )

            if progress_callback:
                progress_callback(100.0, "Download complete!")

            logger.info(f"Model {model_id} downloaded to {model_path}")
            return model_path

        except ImportError:
            # Fallback: use huggingface_hub directly
            try:
                from huggingface_hub import snapshot_download

                if progress_callback:
                    progress_callback(10.0, "Downloading from HuggingFace...")

                snapshot_download(
                    repo_id=f"Systran/faster-whisper-{model_id}",
                    local_dir=str(model_path),
                    local_dir_use_symlinks=False,
                )

                if progress_callback:
                    progress_callback(100.0, "Download complete!")

                logger.info(f"Model {model_id} downloaded to {model_path}")
                return model_path

            except ImportError:
                raise RuntimeError(
                    "Neither faster-whisper nor huggingface_hub is available. "
                    "Please install: pip install faster-whisper"
                )

        except Exception as e:
            # Clean up partial download
            if model_path.exists():
                shutil.rmtree(model_path, ignore_errors=True)
            
            if "connection" in str(e).lower() or "network" in str(e).lower():
                raise ConnectionError(
                    f"Failed to download model {model_id}: No internet connection. "
                    "Please connect to the internet to download models, "
                    "then use the software offline."
                ) from e
            raise RuntimeError(f"Failed to download model {model_id}: {e}") from e

    def delete_model(self, model_id: str) -> bool:
        """Delete a downloaded model to free disk space."""
        model_path = self.models_dir / model_id
        if model_path.exists():
            shutil.rmtree(model_path)
            logger.info(f"Model {model_id} deleted from {model_path}")
            return True
        return False

    def get_disk_usage(self) -> dict:
        """Get disk usage information for all models."""
        total_bytes = 0
        model_sizes = {}
        
        for model_id in AVAILABLE_MODELS:
            model_path = self.models_dir / model_id
            if model_path.exists():
                size = sum(
                    f.stat().st_size
                    for f in model_path.rglob("*")
                    if f.is_file()
                )
                model_sizes[model_id] = size
                total_bytes += size

        return {
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / (1024 * 1024), 1),
            "models": model_sizes,
        }
