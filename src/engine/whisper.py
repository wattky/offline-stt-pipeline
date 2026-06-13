"""
Whisper Engine wrapper for Offline STT Pipeline.
Provides a clean interface to faster-whisper for transcription.
"""

import io
import time
import logging
import tempfile
import platform
from pathlib import Path
from typing import Optional, BinaryIO
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionSegment:
    """A single segment of transcribed text."""
    id: int
    start: float
    end: float
    text: str
    confidence: float
    words: list = field(default_factory=list)


@dataclass
class TranscriptionResult:
    """Complete transcription result."""
    text: str
    segments: list[TranscriptionSegment]
    language: str
    language_probability: float
    duration: float
    processing_time: float


class WhisperEngine:
    """
    Wrapper around faster-whisper for offline speech-to-text.
    
    Provides a simple interface for transcribing audio files and streams,
    with automatic device detection and model management.
    """

    def __init__(
        self,
        model_size_or_path: str = "base",
        device: str = "auto",
        compute_type: str = "auto",
        models_dir: Optional[str] = None,
    ):
        """
        Initialize the Whisper engine.
        
        Args:
            model_size_or_path: Model size ("tiny", "base", etc.) or path to model
            device: Device to use ("auto", "cpu", "cuda")
            compute_type: Computation type ("auto", "int8", "float16", "float32")
            models_dir: Directory containing downloaded models
        """
        self.model_size_or_path = model_size_or_path
        self.device = self._resolve_device(device)
        self.compute_type = self._resolve_compute_type(compute_type)
        self.models_dir = models_dir
        self.model = None
        self._is_loaded = False

    @staticmethod
    def _resolve_device(device: str) -> str:
        """Determine the best available device."""
        if device != "auto":
            return device
        
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        
        return "cpu"

    def _resolve_compute_type(self, compute_type: str) -> str:
        """Determine the best compute type for the device."""
        if compute_type != "auto":
            return compute_type
        
        if self.device == "cuda":
            return "float16"
        elif self.device == "cpu":
            # Use int8 on CPU for better performance
            if platform.machine() in ("x86_64", "AMD64"):
                return "int8"
            return "float32"
        return "float32"

    def load_model(self) -> bool:
        """
        Load the Whisper model into memory.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        if self._is_loaded:
            return True

        try:
            from faster_whisper import WhisperModel

            # Determine model path
            model_path = self.model_size_or_path
            if self.models_dir:
                local_path = Path(self.models_dir) / self.model_size_or_path
                if local_path.exists():
                    model_path = str(local_path)

            logger.info(
                f"Loading Whisper model: {model_path} "
                f"(device={self.device}, compute_type={self.compute_type})"
            )

            self.model = WhisperModel(
                model_path,
                device=self.device,
                compute_type=self.compute_type,
                download_root=self.models_dir,
            )

            self._is_loaded = True
            logger.info("Model loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self._is_loaded = False
            return False

    def unload_model(self):
        """Unload the model from memory."""
        if self.model:
            del self.model
            self.model = None
            self._is_loaded = False
            logger.info("Model unloaded")

    @property
    def is_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self._is_loaded

    def transcribe(
        self,
        audio_data: bytes | np.ndarray | str | Path,
        language: Optional[str] = None,
        beam_size: int = 5,
        vad_filter: bool = True,
        vad_threshold: float = 0.5,
        word_timestamps: bool = False,
        initial_prompt: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Audio as bytes, numpy array, or file path
            language: Language code (None for auto-detect)
            beam_size: Beam size for decoding
            vad_filter: Enable Voice Activity Detection filtering
            vad_threshold: VAD threshold (0.0 - 1.0)
            word_timestamps: Include word-level timestamps
            initial_prompt: Optional prompt to guide transcription
            
        Returns:
            TranscriptionResult with text, segments, and metadata
            
        Raises:
            RuntimeError: If model is not loaded
            ValueError: If audio data is invalid
        """
        if not self._is_loaded:
            raise RuntimeError(
                "Model not loaded. Call load_model() first or download a model."
            )

        start_time = time.time()

        # Handle different input types
        audio_input = self._prepare_audio(audio_data)

        try:
            # Run transcription
            segments_gen, info = self.model.transcribe(
                audio_input,
                language=language if language and language != "auto" else None,
                beam_size=beam_size,
                vad_filter=vad_filter,
                vad_parameters={"threshold": vad_threshold} if vad_filter else None,
                word_timestamps=word_timestamps,
                initial_prompt=initial_prompt,
            )

            # Collect segments
            segments = []
            full_text_parts = []
            
            for i, segment in enumerate(segments_gen):
                words = []
                if word_timestamps and segment.words:
                    words = [
                        {"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
                        for w in segment.words
                    ]

                seg = TranscriptionSegment(
                    id=i,
                    start=segment.start,
                    end=segment.end,
                    text=segment.text.strip(),
                    confidence=segment.avg_logprob,
                    words=words,
                )
                segments.append(seg)
                full_text_parts.append(segment.text.strip())

            processing_time = time.time() - start_time

            return TranscriptionResult(
                text=" ".join(full_text_parts),
                segments=segments,
                language=info.language,
                language_probability=info.language_probability,
                duration=info.duration,
                processing_time=processing_time,
            )

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {e}") from e

    def _prepare_audio(self, audio_data: bytes | np.ndarray | str | Path):
        """
        Prepare audio data for transcription.
        
        Accepts bytes (WAV/MP3/etc), numpy array (float32 16kHz mono),
        or a file path string.
        """
        if isinstance(audio_data, (str, Path)):
            # File path - faster-whisper handles this directly
            path = Path(audio_data)
            if not path.exists():
                raise ValueError(f"Audio file not found: {path}")
            return str(path)

        elif isinstance(audio_data, np.ndarray):
            # Numpy array - should be float32, 16kHz, mono
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            if audio_data.ndim > 1:
                audio_data = audio_data.mean(axis=1)
            return audio_data

        elif isinstance(audio_data, bytes):
            # Raw bytes - write to temp file for processing
            suffix = ".wav"
            tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            tmp.write(audio_data)
            tmp.flush()
            tmp.close()
            return tmp.name

        else:
            raise ValueError(
                f"Unsupported audio data type: {type(audio_data)}. "
                "Expected bytes, numpy array, or file path."
            )

    def get_info(self) -> dict:
        """Get information about the current engine state."""
        return {
            "model": self.model_size_or_path,
            "device": self.device,
            "compute_type": self.compute_type,
            "is_loaded": self._is_loaded,
            "models_dir": self.models_dir,
        }
