"""
Tests for the upload API endpoint.
"""
import io

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestUploadEndpoint:
    """Tests for POST /api/upload."""

    @patch('app.payment.payment_service')
    def test_rejects_empty_file(self, mock_payment, client):
        mock_payment.check_quota = AsyncMock(return_value=(True, 2, 0))

        response = client.post(
            "/api/upload",
            files={"file": ("test.jpg", io.BytesIO(b""), "image/jpeg")},
        )
        assert response.status_code == 400

    @patch('app.payment.payment_service')
    def test_rejects_oversized_file(self, mock_payment, client):
        mock_payment.check_quota = AsyncMock(return_value=(True, 2, 0))

        large_content = b"\x00" * (11 * 1024 * 1024)  # 11MB
        response = client.post(
            "/api/upload",
            files={"file": ("large.jpg", io.BytesIO(large_content), "image/jpeg")},
        )
        assert response.status_code == 413

    @patch('app.payment.payment_service')
    def test_rejects_invalid_mime(self, mock_payment, client):
        mock_payment.check_quota = AsyncMock(return_value=(True, 2, 0))

        # Text file content
        response = client.post(
            "/api/upload",
            files={"file": ("test.txt", io.BytesIO(b"hello world text content"), "text/plain")},
        )
        assert response.status_code == 400

    @patch('app.api.upload.log_upload', new_callable=AsyncMock)
    @patch('app.api.upload.scan_file_for_malware', new_callable=AsyncMock, return_value=True)
    @patch('app.api.upload.storage')
    @patch('app.api.upload.validate_file', new_callable=AsyncMock)
    @patch('app.payment.payment_service')
    def test_successful_upload(
        self, mock_payment, mock_validate, mock_storage,
        mock_scan, mock_log, client
    ):
        # Setup mocks
        mock_payment.check_quota = AsyncMock(return_value=(True, 2, 0))
        mock_validate.return_value = b'\xFF\xD8\xFF\xE0' + b'\x00' * 100

        mock_storage.upload_file = AsyncMock(return_value="blob://test")
        mock_storage.get_file_path = AsyncMock(return_value="/tmp/test.jpg")

        mock_log.return_value = "test-uuid"

        jpeg_content = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b'\x00' * 100
        response = client.post(
            "/api/upload",
            files={"file": ("test.jpg", io.BytesIO(jpeg_content), "image/jpeg")},
        )

        assert response.status_code == 200
        data = response.json()
        assert "upload_id" in data
        assert data["status"] == "uploaded"

    @patch('app.payment.payment_service')
    def test_quota_exceeded_402(self, mock_payment, client):
        mock_payment.check_quota = AsyncMock(return_value=(False, 0, 0))
        mock_payment.FREE_TIER_LIMIT = 2
        mock_payment.CREDIT_PACKS = {
            "pack_5": {"credits": 5, "price_nok": 39_00, "name": "5-pack"},
        }

        jpeg_content = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b'\x00' * 100
        response = client.post(
            "/api/upload",
            files={"file": ("test.jpg", io.BytesIO(jpeg_content), "image/jpeg")},
        )

        assert response.status_code == 402
        data = response.json()
        assert data["error"] == "quota_exceeded"
        assert "credit_packs" in data

    @patch('app.api.upload.deduct_credit', new_callable=AsyncMock, return_value=True)
    @patch('app.api.upload.log_upload', new_callable=AsyncMock)
    @patch('app.api.upload.scan_file_for_malware', new_callable=AsyncMock, return_value=True)
    @patch('app.api.upload.storage')
    @patch('app.api.upload.validate_file', new_callable=AsyncMock)
    @patch('app.payment.payment_service')
    def test_upload_deducts_credit_when_free_exhausted(
        self, mock_payment, mock_validate, mock_storage,
        mock_scan, mock_log, mock_deduct, client
    ):
        # Free exhausted, but has credits
        mock_payment.check_quota = AsyncMock(return_value=(True, 0, 5))
        mock_validate.return_value = b'\xFF\xD8\xFF\xE0' + b'\x00' * 100
        mock_storage.upload_file = AsyncMock(return_value="blob://test")
        mock_storage.get_file_path = AsyncMock(return_value="/tmp/test.jpg")
        mock_log.return_value = "test-uuid"

        jpeg_content = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b'\x00' * 100
        response = client.post(
            "/api/upload",
            files={"file": ("test.jpg", io.BytesIO(jpeg_content), "image/jpeg")},
        )

        assert response.status_code == 200
        mock_deduct.assert_called_once()
