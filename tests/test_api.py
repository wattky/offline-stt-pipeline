"""
Tests for the Offline STT Pipeline API.
Run with: pytest tests/ -v
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client."""
    from src.api import create_app
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_has_required_fields(self, client):
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "uptime_seconds" in data


class TestModelsEndpoint:
    """Tests for the /v1/models endpoint."""

    def test_list_models_returns_200(self, client):
        response = client.get("/v1/models")
        assert response.status_code == 200

    def test_list_models_has_data(self, client):
        response = client.get("/v1/models")
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0

    def test_model_has_required_fields(self, client):
        response = client.get("/v1/models")
        data = response.json()
        model = data["data"][0]
        assert "id" in model
        assert "name" in model
        assert "size_mb" in model
        assert "is_downloaded" in model


class TestLanguagesEndpoint:
    """Tests for the /v1/languages endpoint."""

    def test_languages_returns_200(self, client):
        response = client.get("/v1/languages")
        assert response.status_code == 200

    def test_languages_has_auto(self, client):
        response = client.get("/v1/languages")
        data = response.json()
        assert "auto" in data["languages"]


class TestTranscriptionEndpoint:
    """Tests for the /v1/audio/transcriptions endpoint."""

    def test_transcription_requires_file(self, client):
        response = client.post("/v1/audio/transcriptions")
        assert response.status_code == 422  # Validation error

    def test_transcription_returns_503_without_model(self, client):
        """Without a loaded model, should return 503."""
        # Create a minimal WAV file
        import struct
        wav_data = b'RIFF' + struct.pack('<I', 36) + b'WAVEfmt '
        wav_data += struct.pack('<IHHIIHH', 16, 1, 1, 16000, 32000, 2, 16)
        wav_data += b'data' + struct.pack('<I', 0)
        
        response = client.post(
            "/v1/audio/transcriptions",
            files={"file": ("test.wav", wav_data, "audio/wav")},
        )
        # Should be 503 (no model) or 500 (processing error)
        assert response.status_code in (503, 500)


class TestStatsEndpoint:
    """Tests for the /v1/stats endpoint."""

    def test_stats_returns_200(self, client):
        response = client.get("/v1/stats")
        assert response.status_code == 200

    def test_stats_has_required_fields(self, client):
        response = client.get("/v1/stats")
        data = response.json()
        assert "total_requests" in data
        assert "total_audio_seconds" in data
        assert "uptime_seconds" in data


class TestConfigEndpoint:
    """Tests for the /v1/config endpoint."""

    def test_config_returns_200(self, client):
        response = client.get("/v1/config")
        assert response.status_code == 200

    def test_config_has_required_fields(self, client):
        response = client.get("/v1/config")
        data = response.json()
        assert "host" in data
        assert "port" in data
        assert "model" in data
