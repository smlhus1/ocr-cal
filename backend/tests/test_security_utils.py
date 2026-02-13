"""
Tests for security utility functions in security.py.
Covers download tokens, file signature validation, user identifier, country code.
"""
import time

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from app.security import (
    generate_download_token,
    validate_download_token,
    validate_file_signature,
    get_user_identifier,
    get_country_code,
)


class TestDownloadToken:
    """Tests for download token generation and validation."""

    @patch('app.security.settings')
    def test_generate_and_validate(self, mock_settings):
        mock_settings.secret_salt = "test_salt"
        token = generate_download_token("upload-123")
        # Should not raise
        validate_download_token("upload-123", token)

    @patch('app.security.settings')
    def test_expired_token_rejected(self, mock_settings):
        mock_settings.secret_salt = "test_salt"
        token = generate_download_token("upload-123")

        # Tamper with expiry to make it expired
        parts = token.split(":")
        expired_time = str(int(time.time()) - 100)
        # Need to re-sign with expired time
        import hmac
        import hashlib
        message = f"upload-123:{expired_time}".encode()
        signature = hmac.new(
            "test_salt".encode(), message, hashlib.sha256
        ).hexdigest()
        expired_token = f"{expired_time}:{signature}"

        with pytest.raises(HTTPException) as exc_info:
            validate_download_token("upload-123", expired_token)
        assert exc_info.value.status_code == 403

    @patch('app.security.settings')
    def test_wrong_upload_id_rejected(self, mock_settings):
        mock_settings.secret_salt = "test_salt"
        token = generate_download_token("upload-123")

        with pytest.raises(HTTPException) as exc_info:
            validate_download_token("upload-456", token)
        assert exc_info.value.status_code == 403

    @patch('app.security.settings')
    def test_tampered_signature_rejected(self, mock_settings):
        mock_settings.secret_salt = "test_salt"
        token = generate_download_token("upload-123")

        # Tamper with signature
        parts = token.split(":")
        tampered_token = f"{parts[0]}:{'a' * 64}"

        with pytest.raises(HTTPException) as exc_info:
            validate_download_token("upload-123", tampered_token)
        assert exc_info.value.status_code == 403

    @patch('app.security.settings')
    def test_malformed_token_rejected(self, mock_settings):
        mock_settings.secret_salt = "test_salt"

        with pytest.raises(HTTPException) as exc_info:
            validate_download_token("upload-123", "garbage")
        assert exc_info.value.status_code == 403

    @patch('app.security.settings')
    def test_empty_token_rejected(self, mock_settings):
        mock_settings.secret_salt = "test_salt"

        with pytest.raises(HTTPException):
            validate_download_token("upload-123", "")


class TestValidateFileSignature:
    """Tests for validate_file_signature()."""

    def test_valid_jpeg(self):
        content = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b'\x00' * 100
        assert validate_file_signature(content, "image/jpeg") is True

    def test_valid_jpeg_e1(self):
        content = bytes([0xFF, 0xD8, 0xFF, 0xE1]) + b'\x00' * 100
        assert validate_file_signature(content, "image/jpeg") is True

    def test_valid_png(self):
        content = bytes([0x89, 0x50, 0x4E, 0x47]) + b'\x00' * 100
        assert validate_file_signature(content, "image/png") is True

    def test_valid_pdf(self):
        content = bytes([0x25, 0x50, 0x44, 0x46]) + b'\x00' * 100
        assert validate_file_signature(content, "application/pdf") is True

    def test_mismatched_type(self):
        # JPEG bytes but claiming PNG
        content = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b'\x00' * 100
        assert validate_file_signature(content, "image/png") is False

    def test_too_small_file(self):
        content = b'\xFF\xD8'  # Only 2 bytes
        assert validate_file_signature(content, "image/jpeg") is False

    def test_unknown_mime_type(self):
        content = b'\x00' * 100
        assert validate_file_signature(content, "application/octet-stream") is False

    def test_empty_content(self):
        assert validate_file_signature(b'', "image/jpeg") is False


class TestGetUserIdentifier:
    """Tests for get_user_identifier()."""

    @patch('app.security.settings')
    def test_deterministic(self, mock_settings):
        mock_settings.secret_salt = "test_salt"
        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.headers = {}

        id1 = get_user_identifier(request)
        id2 = get_user_identifier(request)
        assert id1 == id2

    @patch('app.security.settings')
    def test_different_ips(self, mock_settings):
        mock_settings.secret_salt = "test_salt"

        req1 = MagicMock()
        req1.client.host = "192.168.1.1"
        req1.headers = {}

        req2 = MagicMock()
        req2.client.host = "10.0.0.1"
        req2.headers = {}

        id1 = get_user_identifier(req1)
        id2 = get_user_identifier(req2)
        assert id1 != id2

    @patch('app.security.settings')
    def test_returns_16_chars(self, mock_settings):
        mock_settings.secret_salt = "test_salt"
        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.headers = {}

        identifier = get_user_identifier(request)
        assert len(identifier) == 16


class TestGetCountryCode:
    """Tests for get_country_code()."""

    def test_cloudflare_header(self):
        request = MagicMock()
        request.headers = {"CF-IPCountry": "NO"}
        assert get_country_code(request) == "NO"

    def test_xx_ignored(self):
        request = MagicMock()
        request.headers = {"CF-IPCountry": "XX"}
        # XX means unknown in CloudFlare
        result = get_country_code(request)
        # Should fall through to X-Country-Code or None
        assert result != "XX" or result is None

    def test_x_country_code_header(self):
        request = MagicMock()
        request.headers = {"X-Country-Code": "SE"}
        assert get_country_code(request) == "SE"

    def test_no_headers_returns_none(self):
        request = MagicMock()
        request.headers = {}
        assert get_country_code(request) is None
