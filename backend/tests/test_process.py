"""
Tests for OCR processing pipeline.
"""
import pytest
from pydantic import ValidationError

from app.ocr.confidence_scorer import (
    calculate_confidence,
    validate_shift,
    assign_individual_confidences,
    generate_warnings,
)
from app.models import Shift


class TestValidateShift:
    """Tests for shift validation."""

    def test_valid_shift(self):
        shift = Shift(
            date="01.12.2025",
            start_time="07:00",
            end_time="15:00",
            shift_type="tidlig",
            confidence=0.9
        )
        assert validate_shift(shift) is True

    def test_invalid_date_format_rejected_by_pydantic(self):
        """Pydantic now rejects invalid date formats at construction."""
        with pytest.raises(ValidationError):
            Shift(
                date="2025-12-01",
                start_time="07:00",
                end_time="15:00",
                shift_type="tidlig",
                confidence=0.9
            )

    def test_invalid_time(self):
        """25:00 matches HH:MM pattern but validate_shift catches invalid hour."""
        shift = Shift(
            date="01.12.2025",
            start_time="25:00",
            end_time="15:00",
            shift_type="tidlig",
            confidence=0.9
        )
        assert validate_shift(shift) is False

    def test_invalid_shift_type_rejected_by_pydantic(self):
        """Pydantic now rejects invalid shift types at construction."""
        with pytest.raises(ValidationError):
            Shift(
                date="01.12.2025",
                start_time="07:00",
                end_time="15:00",
                shift_type="invalid",
                confidence=0.9
            )


class TestConfidenceScoring:
    """Tests for confidence calculation."""

    def test_high_confidence_text(self):
        ocr_text = "desember 2025\nmandag 07:00 - 15:00\n1"
        shifts = [
            Shift(
                date="01.12.2025",
                start_time="07:00",
                end_time="15:00",
                shift_type="tidlig",
                confidence=0.9
            )
        ]
        score = calculate_confidence(ocr_text, shifts)
        assert score > 0.7

    def test_empty_text_low_confidence(self):
        score = calculate_confidence("", [])
        assert score < 0.3

    def test_no_shifts_moderate_confidence(self):
        ocr_text = "desember 2025\nrandom text"
        score = calculate_confidence(ocr_text, [])
        assert score < 0.6


class TestGenerateWarnings:
    """Tests for warning generation."""

    def test_low_confidence_warning(self):
        shifts = []
        warnings = generate_warnings(shifts, 0.3)
        assert any("Lav sikkerhet" in w for w in warnings)

    def test_short_shift_warning(self):
        shifts = [
            Shift(
                date="01.12.2025",
                start_time="07:00",
                end_time="09:00",
                shift_type="tidlig",
                confidence=0.9
            )
        ]
        warnings = generate_warnings(shifts, 0.9)
        assert any("kort" in w for w in warnings)

    def test_no_warnings_for_normal_shifts(self):
        shifts = [
            Shift(
                date="01.12.2025",
                start_time="07:00",
                end_time="15:00",
                shift_type="tidlig",
                confidence=0.9
            )
        ]
        warnings = generate_warnings(shifts, 0.9)
        assert len(warnings) == 0
