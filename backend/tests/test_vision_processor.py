"""
Tests for VisionProcessor with mocked OpenAI client.
No actual API calls are made.
"""
import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from pathlib import Path

from app.ocr.vision_processor import VisionProcessor, SUPPORTED_MIME_TYPES


def _make_mock_response(shifts_data, notes=None, prompt_tokens=100, completion_tokens=50):
    """Create a mock OpenAI ChatCompletion response."""
    payload = {"shifts": shifts_data}
    if notes:
        payload["notes"] = notes

    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(payload)

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = prompt_tokens
    mock_usage.completion_tokens = completion_tokens
    mock_usage.total_tokens = prompt_tokens + completion_tokens

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage
    return mock_response


def _make_processor():
    """Create a VisionProcessor with mocked OpenAI client."""
    proc = VisionProcessor.__new__(VisionProcessor)
    proc.client = MagicMock()
    return proc


class TestVisionProcessorParsing:
    """Tests for Vision API response parsing."""

    def test_valid_response_parsed(self, tmp_path):
        """Valid JSON response is correctly parsed into Shift objects."""
        proc = _make_processor()
        proc.client.chat.completions.create.return_value = _make_mock_response([
            {"date": "01.12.2025", "start_time": "07:00", "end_time": "15:00",
             "shift_type": "tidlig", "confidence": 0.95},
            {"date": "02.12.2025", "start_time": "14:00", "end_time": "22:00",
             "shift_type": "mellom", "confidence": 0.90},
        ])

        # Create a small test image file
        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 100)

        shifts, confidence = proc.process_image(str(img_file))
        assert len(shifts) == 2
        assert shifts[0].date == "01.12.2025"
        assert shifts[0].confidence == 0.95
        assert shifts[1].shift_type == "mellom"
        # Overall confidence = average
        assert abs(confidence - 0.925) < 0.01

    def test_missing_field_skipped(self, tmp_path):
        """Shift with missing required field is skipped, not crash."""
        proc = _make_processor()
        proc.client.chat.completions.create.return_value = _make_mock_response([
            {"date": "01.12.2025", "start_time": "07:00", "end_time": "15:00",
             "shift_type": "tidlig", "confidence": 0.95},
            {"date": "02.12.2025"},  # Missing start_time, end_time, shift_type
        ])

        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 100)

        shifts, confidence = proc.process_image(str(img_file))
        assert len(shifts) == 1  # Only the valid shift
        assert shifts[0].date == "01.12.2025"

    def test_confidence_from_response(self, tmp_path):
        """Confidence is read from API response, not hardcoded."""
        proc = _make_processor()
        proc.client.chat.completions.create.return_value = _make_mock_response([
            {"date": "01.12.2025", "start_time": "07:00", "end_time": "15:00",
             "shift_type": "tidlig", "confidence": 0.72},
        ])

        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 100)

        shifts, confidence = proc.process_image(str(img_file))
        assert shifts[0].confidence == 0.72
        assert abs(confidence - 0.72) < 0.01

    def test_confidence_clamped(self, tmp_path):
        """Confidence > 1.0 is clamped to 1.0, < 0.0 to 0.0."""
        proc = _make_processor()
        proc.client.chat.completions.create.return_value = _make_mock_response([
            {"date": "01.12.2025", "start_time": "07:00", "end_time": "15:00",
             "shift_type": "tidlig", "confidence": 1.5},
        ])

        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 100)

        shifts, _ = proc.process_image(str(img_file))
        assert shifts[0].confidence == 1.0

    def test_missing_confidence_defaults(self, tmp_path):
        """Missing confidence field defaults to 0.85."""
        proc = _make_processor()
        proc.client.chat.completions.create.return_value = _make_mock_response([
            {"date": "01.12.2025", "start_time": "07:00", "end_time": "15:00",
             "shift_type": "tidlig"},
        ])

        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 100)

        shifts, _ = proc.process_image(str(img_file))
        assert shifts[0].confidence == 0.85

    def test_empty_shifts_returns_empty(self, tmp_path):
        """Empty shifts array returns empty list, confidence 0.0."""
        proc = _make_processor()
        proc.client.chat.completions.create.return_value = _make_mock_response([])

        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 100)

        shifts, confidence = proc.process_image(str(img_file))
        assert shifts == []
        assert confidence == 0.0

    def test_notes_logged(self, tmp_path, caplog):
        """Vision API notes are logged as info."""
        proc = _make_processor()
        proc.client.chat.completions.create.return_value = _make_mock_response(
            [], notes="Could not read blurry section"
        )

        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 100)

        with caplog.at_level("INFO", logger="shiftsync"):
            proc.process_image(str(img_file))

        assert "Could not read blurry section" in caplog.text

    def test_empty_response_raises(self, tmp_path):
        """Empty API response raises ValueError."""
        proc = _make_processor()
        mock_choice = MagicMock()
        mock_choice.message.content = ""
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = None
        proc.client.chat.completions.create.return_value = mock_response

        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 100)

        with pytest.raises(ValueError, match="empty response"):
            proc.process_image(str(img_file))


class TestMimeType:
    """Tests for MIME type detection."""

    def test_jpg_mime(self):
        assert SUPPORTED_MIME_TYPES['.jpg'] == 'image/jpeg'

    def test_png_mime(self):
        assert SUPPORTED_MIME_TYPES['.png'] == 'image/png'

    def test_jpeg_mime(self):
        assert SUPPORTED_MIME_TYPES['.jpeg'] == 'image/jpeg'


class TestImageEncoding:
    """Tests for image encoding and compression."""

    def test_small_image_not_compressed(self, tmp_path):
        """Images under 2MB are sent as-is."""
        proc = _make_processor()
        img_file = tmp_path / "small.png"
        img_file.write_bytes(b'\x89PNG' + b'\x00' * 100)

        data, mime = proc._encode_image(str(img_file))
        assert mime == 'image/png'
        assert len(data) > 0

    def test_large_image_compressed(self, tmp_path):
        """Images over 2MB are compressed to JPEG."""
        from PIL import Image as PILImage
        import random
        proc = _make_processor()

        # Create a noisy image that won't compress well as PNG (> 2MB)
        random.seed(42)
        img = PILImage.new('RGB', (2000, 2000))
        pixels = [
            (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            for _ in range(2000 * 2000)
        ]
        img.putdata(pixels)
        img_file = tmp_path / "large.png"
        img.save(str(img_file))

        # Verify file is actually > 2MB
        assert img_file.stat().st_size > 2 * 1024 * 1024

        data, mime = proc._encode_image(str(img_file))
        # Large PNG gets compressed to JPEG
        assert mime == 'image/jpeg'


class TestRetryLogic:
    """Tests for retry behavior on transient failures."""

    def test_retry_on_rate_limit(self, tmp_path):
        """RateLimitError triggers retry, succeeds on second attempt."""
        from openai import RateLimitError

        proc = _make_processor()

        # First call raises RateLimitError, second succeeds
        mock_error_response = MagicMock()
        mock_error_response.status_code = 429
        mock_error_response.headers = {}
        mock_error_response.json.return_value = {"error": {"message": "rate limited"}}

        proc.client.chat.completions.create.side_effect = [
            RateLimitError(
                message="rate limited",
                response=mock_error_response,
                body={"error": {"message": "rate limited"}},
            ),
            _make_mock_response([
                {"date": "01.12.2025", "start_time": "07:00", "end_time": "15:00",
                 "shift_type": "tidlig", "confidence": 0.9},
            ]),
        ]

        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 100)

        shifts, _ = proc.process_image(str(img_file))
        assert len(shifts) == 1
        assert proc.client.chat.completions.create.call_count == 2


class TestTokenLogging:
    """Tests for token usage logging."""

    def test_tokens_logged(self, tmp_path, caplog):
        """Token usage is logged after successful API call."""
        proc = _make_processor()
        proc.client.chat.completions.create.return_value = _make_mock_response(
            [{"date": "01.12.2025", "start_time": "07:00", "end_time": "15:00",
              "shift_type": "tidlig", "confidence": 0.9}],
            prompt_tokens=500, completion_tokens=200,
        )

        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 100)

        with caplog.at_level("INFO", logger="shiftsync"):
            proc.process_image(str(img_file))

        assert "prompt=500" in caplog.text
        assert "completion=200" in caplog.text
        assert "total=700" in caplog.text
