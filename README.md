# Offline STT Pipeline

**Cross-platform, fully offline Speech-to-Text API pipeline for Voice AI integration.**

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

Offline STT Pipeline is a lightweight desktop application and service that runs a local OpenAI-compatible REST API for speech-to-text transcription. It acts as a drop-in replacement for cloud STT services, allowing Voice AI applications to process audio locally without internet access, saving on API costs and ensuring absolute privacy.

## Features

- **100% Offline**: Works completely without internet connection (after initial model download).
- **Cross-Platform**: Available for Windows, macOS, and Linux.
- **OpenAI-Compatible API**: Drop-in replacement for OpenAI's `/v1/audio/transcriptions` endpoint.
- **High Performance**: Powered by `faster-whisper` (CTranslate2 backend) for up to 4x faster transcription than standard Whisper.
- **Hardware Acceleration**: Automatic CPU/GPU detection (CUDA support).
- **Web UI**: Built-in modern dashboard for testing and model management.
- **Multi-language**: Supports 99+ languages with auto-detection.

## Architecture

```text
User Device (Microphone) -> Voice AI App -> Offline STT Pipeline (Local API) -> Text -> Voice AI App
```

By placing this pipeline between the user and the Voice AI, the AI service receives pre-transcribed text, eliminating the need for the AI provider to perform expensive cloud-based STT.

## Installation

### Method 1: Standalone Executable (Recommended)
Download the latest release for your operating system from the [Releases page](../../releases).
- **Windows**: Run `offline-stt-pipeline-windows.exe`
- **macOS**: Run `offline-stt-pipeline-macos`
- **Linux**: Run `offline-stt-pipeline-linux`

### Method 2: Install via Script (Linux/macOS)
```bash
git clone https://github.com/offline-stt-pipeline/offline-stt-pipeline.git
cd offline-stt-pipeline
./scripts/install.sh
```

### Method 3: Install via Script (Windows)
```cmd
git clone https://github.com/offline-stt-pipeline/offline-stt-pipeline.git
cd offline-stt-pipeline
scripts\install.bat
```

### Method 4: Docker
```bash
docker-compose up -d
```

## Usage

Start the server:
```bash
offline-stt
```

Options:
```text
  --host HOST           Host to bind the server to (default: 0.0.0.0)
  --port PORT           Port to run the server on (default: 8000)
  --model MODEL         Model to load at startup (e.g., base, small)
  --device {auto,cpu,cuda} Device to use for inference
  --no-browser          Don't open the web UI in browser on startup
```

Once running, the Web UI will open automatically at `http://localhost:8000`.

## API Documentation

The API provides an OpenAI-compatible endpoint. You can view the full interactive Swagger documentation at `http://localhost:8000/docs`.

### 1. Transcribe Audio (OpenAI Compatible)

```bash
curl -X POST http://localhost:8000/v1/audio/transcriptions \
  -F "file=@audio.wav" \
  -F "model=base" \
  -F "response_format=json"
```

**Response:**
```json
{
  "text": "Hello, this is a test of the offline speech to text pipeline."
}
```

### 2. Download a Model

Before transcribing offline, you must download a model while connected to the internet.

```bash
curl -X POST http://localhost:8000/v1/models/download/base
```

### 3. List Available Models

```bash
curl http://localhost:8000/v1/models
```

## Available Models

| Model | Size | RAM Required | Speed | Accuracy |
|-------|------|--------------|-------|----------|
| `tiny` | 75 MB | ~300 MB | Fastest | Lowest |
| `base` | 142 MB | ~500 MB | Fast | Balanced |
| `small` | 466 MB | ~1.0 GB | Medium | Good |
| `medium` | 1.5 GB | ~2.5 GB | Slow | High |
| `large-v3` | 3.0 GB | ~4.5 GB | Slowest | Highest |

## Integration Example (Python)

If your Voice AI app uses the official `openai` Python package, you can simply change the base URL:

```python
from openai import OpenAI

# Point the client to the local Offline STT Pipeline
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed-for-local"
)

# Transcribe locally
with open("speech.wav", "rb") as audio_file:
    transcription = client.audio.transcriptions.create(
        model="base",
        file=audio_file
    )

print(transcription.text)
```

## Building from Source

To build standalone executables using PyInstaller:

```bash
pip install -r requirements.txt
pip install pyinstaller
python build.py --onefile
```

The output will be in the `dist/` directory.

## License

MIT License. See LICENSE file for details.
