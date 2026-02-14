"""
Tests for download/calendar generation API endpoints.
"""
import pytest
from unittest.mock import patch


class TestGenerateCalendar:
    """Tests for POST /api/generate-calendar."""

    def test_generate_calendar_success(self, client):
        response = client.post("/api/generate-calendar", json={
            "shifts": [
                {
                    "date": "15.01.2025",
                    "start_time": "07:00",
                    "end_time": "15:00",
                    "shift_type": "tidlig",
                    "confidence": 0.95,
                }
            ],
            "owner_name": "Test User",
        })

        assert response.status_code == 200
        assert "text/calendar" in response.headers.get("content-type", "")
        content = response.content.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "BEGIN:VEVENT" in content
        assert "Test User" in content

    def test_empty_shifts_rejected(self, client):
        response = client.post("/api/generate-calendar", json={
            "shifts": [],
            "owner_name": "Test User",
        })
        # min_length=1 in GenerateCalendarRequest
        assert response.status_code == 422

    def test_xss_in_owner_sanitized(self, client):
        response = client.post("/api/generate-calendar", json={
            "shifts": [
                {
                    "date": "15.01.2025",
                    "start_time": "07:00",
                    "end_time": "15:00",
                    "shift_type": "tidlig",
                    "confidence": 0.95,
                }
            ],
            "owner_name": "<script>alert('xss')</script>",
        })

        if response.status_code == 200:
            content = response.content.decode("utf-8")
            assert "<script>" not in content

    def test_multiple_shifts_in_output(self, client, sample_shifts):
        shifts_data = [s.model_dump() for s in sample_shifts]
        response = client.post("/api/generate-calendar", json={
            "shifts": shifts_data,
            "owner_name": "Ola",
        })

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert content.count("BEGIN:VEVENT") == 3

    def test_content_disposition_header(self, client):
        response = client.post("/api/generate-calendar", json={
            "shifts": [
                {
                    "date": "15.01.2025",
                    "start_time": "07:00",
                    "end_time": "15:00",
                    "shift_type": "tidlig",
                    "confidence": 0.95,
                }
            ],
            "owner_name": "Ola",
        })

        assert response.status_code == 200
        disposition = response.headers.get("content-disposition", "")
        assert "attachment" in disposition
        assert ".ics" in disposition


class TestDownloadToken:
    """Tests for POST /api/download-token/{upload_id}."""

    def test_download_token_roundtrip(self, client):
        # Get a token (session_id comes from session middleware)
        response = client.post("/api/download-token/test-upload-123")
        assert response.status_code == 200
        data = response.json()
        assert "token" in data

    def test_expired_token_rejected(self, client):
        # Use a clearly expired token
        response = client.get(
            "/api/download/test-upload-123",
            params={"token": "1000000000:fakesignature"},
        )
        assert response.status_code == 403

    def test_token_from_different_session_rejected(self, client):
        """A token generated for one session should not work with a different session."""
        from app.security import generate_download_token

        with patch('app.security.settings') as mock_settings:
            mock_settings.secret_salt = "test_salt_for_testing"
            # Generate token for session-A
            token = generate_download_token("test-upload-456", "session-A")

        # Client will have its own session_id (not "session-A"),
        # so validation should fail
        response = client.get(
            "/api/download/test-upload-456",
            params={"token": token},
        )
        assert response.status_code == 403
