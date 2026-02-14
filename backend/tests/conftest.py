"""
Shared test fixtures for ShiftSync backend tests.

Env vars are set BEFORE any app module imports to ensure
database.py and config.py get test values at module-init time.
"""
import os

# Set test env vars before any app imports
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_SALT", "test_salt_for_testing")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("INTERNAL_API_KEY", "test_api_key_12345")

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.models import Shift


@pytest.fixture
def test_settings():
    """Mock settings for testing."""
    with patch('app.config.settings') as mock_settings:
        mock_settings.environment = "testing"
        mock_settings.secret_salt = "test_salt_for_testing"
        mock_settings.internal_api_key = "test_api_key_12345"
        mock_settings.database_url = "sqlite+aiosqlite:///:memory:"
        mock_settings.max_file_size_mb = 10
        mock_settings.rate_limit_per_minute = 10
        mock_settings.frontend_url = "http://localhost:3000"
        mock_settings.stripe_secret_key = None
        mock_settings.stripe_webhook_secret = None
        mock_settings.sentry_dsn = None
        mock_settings.azure_application_insights_key = None
        mock_settings.applicationinsights_connection_string = None
        mock_settings.tesseract_path = "/usr/bin/tesseract"
        mock_settings.ocr_language = "nor"
        yield mock_settings


@pytest.fixture
def client(test_settings):
    """Create test client with mocked dependencies."""
    from app.main import app, _session_creation_times
    # Clear session rate limiter between tests to prevent 429s
    _session_creation_times.clear()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def api_key_header():
    """Return valid API key header."""
    return {"X-API-Key": "test_api_key_12345"}


@pytest.fixture
def sample_shifts():
    """Sample shifts for testing (tidlig, kveld, natt)."""
    return [
        Shift(
            date="15.01.2025",
            start_time="07:00",
            end_time="15:00",
            shift_type="tidlig",
            confidence=0.95,
        ),
        Shift(
            date="16.01.2025",
            start_time="16:00",
            end_time="23:00",
            shift_type="kveld",
            confidence=0.85,
        ),
        Shift(
            date="17.01.2025",
            start_time="22:00",
            end_time="06:00",
            shift_type="natt",
            confidence=0.90,
        ),
    ]
