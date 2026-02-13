"""
Tests for OCR processor shift extraction and classification.
Tests _extract_shifts() and _determine_shift_type() WITHOUT Tesseract.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.models import Shift


def _make_processor():
    """Create VaktplanProcessor with mocked Tesseract path."""
    with patch('app.ocr.processor.Path') as mock_path:
        mock_path.return_value.exists.return_value = True
        from app.ocr.processor import VaktplanProcessor
        return VaktplanProcessor(tesseract_path="/fake/tesseract")


class TestDetermineShiftType:
    """Tests for _determine_shift_type()."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.proc = _make_processor()

    def test_tidlig_07(self):
        assert self.proc._determine_shift_type("07:00", "15:00") == "tidlig"

    def test_tidlig_09(self):
        assert self.proc._determine_shift_type("09:00", "17:00") == "tidlig"

    def test_mellom_13(self):
        assert self.proc._determine_shift_type("13:00", "21:00") == "mellom"

    def test_kveld_17(self):
        assert self.proc._determine_shift_type("17:00", "01:00") == "kveld"

    def test_natt_23(self):
        assert self.proc._determine_shift_type("23:00", "07:00") == "natt"

    def test_boundary_06(self):
        assert self.proc._determine_shift_type("06:00", "14:00") == "tidlig"

    def test_boundary_12(self):
        assert self.proc._determine_shift_type("12:00", "20:00") == "mellom"

    def test_boundary_16(self):
        assert self.proc._determine_shift_type("16:00", "00:00") == "kveld"

    def test_boundary_22(self):
        assert self.proc._determine_shift_type("22:00", "06:00") == "natt"

    def test_natt_crossing_22_06(self):
        result = self.proc._determine_shift_type("22:00", "06:00")
        assert result == "natt"

    def test_natt_early_morning(self):
        result = self.proc._determine_shift_type("03:00", "08:00")
        assert result == "natt"


class TestExtractShifts:
    """Tests for _extract_shifts()."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.proc = _make_processor()

    def test_single_shift(self):
        text = "desember 2025\nmandag 07:00 - 15:00\n1"
        shifts = self.proc._extract_shifts(text)
        assert len(shifts) == 1
        assert shifts[0].date == "01.12.2025"
        assert shifts[0].start_time == "07:00"
        assert shifts[0].end_time == "15:00"
        assert shifts[0].shift_type == "tidlig"

    def test_multiple_shifts(self):
        text = (
            "desember 2025\n"
            "mandag 07:00 - 15:00\n1\n"
            "tirsdag 15:00 - 23:00\n2\n"
            "onsdag 22:00 - 06:00\n3"
        )
        shifts = self.proc._extract_shifts(text)
        assert len(shifts) == 3

    def test_multi_month(self):
        text = (
            "november 2025\n"
            "mandag 07:00 - 15:00\n28\n"
            "desember 2025\n"
            "mandag 07:00 - 15:00\n5"
        )
        shifts = self.proc._extract_shifts(text)
        assert len(shifts) == 2
        # First shift in November
        assert shifts[0].date == "28.11.2025"
        # Second shift in December
        assert shifts[1].date == "05.12.2025"

    def test_space_in_day_number(self):
        text = "desember 2025\nmandag 07:00 - 15:00\n2 3"
        shifts = self.proc._extract_shifts(text)
        assert len(shifts) == 1
        assert shifts[0].date == "23.12.2025"

    def test_no_month_returns_empty(self):
        text = "some random text without month names"
        shifts = self.proc._extract_shifts(text)
        assert shifts == []

    def test_duplicate_deduplicated(self):
        text = (
            "desember 2025\n"
            "mandag 07:00 - 15:00\n1\n"
            "mandag 07:00 - 15:00\n1"
        )
        shifts = self.proc._extract_shifts(text)
        assert len(shifts) == 1

    def test_invalid_day_skipped(self):
        # Day 0 should be skipped
        text = "desember 2025\nmandag 07:00 - 15:00\n0"
        shifts = self.proc._extract_shifts(text)
        assert len(shifts) == 0

    def test_day_32_skipped(self):
        text = "desember 2025\nmandag 07:00 - 15:00\n32"
        shifts = self.proc._extract_shifts(text)
        assert len(shifts) == 0

    def test_all_weekdays(self):
        days = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
        for i, day in enumerate(days):
            day_num = i + 1
            text = f"desember 2025\n{day} 07:00 - 15:00\n{day_num}"
            shifts = self.proc._extract_shifts(text)
            assert len(shifts) == 1, f"Failed for {day}"

    def test_lordag_variant(self):
        # OCR might render "lørdag" as "l.rdag"
        text = "desember 2025\nl.rdag 07:00 - 15:00\n6"
        shifts = self.proc._extract_shifts(text)
        assert len(shifts) == 1

    def test_shift_types_correct(self):
        text = (
            "desember 2025\n"
            "mandag 07:00 - 15:00\n1\n"
            "tirsdag 13:00 - 21:00\n2\n"
            "onsdag 17:00 - 01:00\n3\n"
            "torsdag 22:00 - 06:00\n4"
        )
        shifts = self.proc._extract_shifts(text)
        assert len(shifts) == 4
        assert shifts[0].shift_type == "tidlig"
        assert shifts[1].shift_type == "mellom"
        assert shifts[2].shift_type == "kveld"
        assert shifts[3].shift_type == "natt"

    def test_shifts_have_correct_confidence(self):
        text = "desember 2025\nmandag 07:00 - 15:00\n1"
        shifts = self.proc._extract_shifts(text)
        assert shifts[0].confidence == 1.0  # Default before confidence scorer


class TestTimeValidation:
    """Tests for time validation in shift extraction."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.proc = _make_processor()

    def test_invalid_hour_25_rejected(self):
        text = "desember 2025\nmandag 25:00 - 15:00\n1"
        shifts = self.proc._extract_shifts(text)
        assert len(shifts) == 0

    def test_invalid_minute_60_rejected(self):
        text = "desember 2025\nmandag 07:60 - 15:00\n1"
        shifts = self.proc._extract_shifts(text)
        assert len(shifts) == 0

    def test_invalid_end_hour_rejected(self):
        text = "desember 2025\nmandag 07:00 - 25:00\n1"
        shifts = self.proc._extract_shifts(text)
        assert len(shifts) == 0

    def test_garbage_between_time_and_day_rejected(self):
        """Non-whitespace text between time and day should not match."""
        text = "desember 2025\nmandag 07:00 - 15:00 some random text 1"
        shifts = self.proc._extract_shifts(text)
        assert len(shifts) == 0

    def test_valid_boundary_23_59(self):
        text = "desember 2025\nmandag 23:59 - 07:00\n1"
        shifts = self.proc._extract_shifts(text)
        assert len(shifts) == 1

    def test_valid_boundary_00_00(self):
        text = "desember 2025\nmandag 00:00 - 08:00\n1"
        shifts = self.proc._extract_shifts(text)
        assert len(shifts) == 1


class TestOtsuThreshold:
    """Tests for the Otsu threshold calculator."""

    def setup_method(self):
        self.proc = _make_processor()

    def test_returns_int(self):
        """Otsu threshold should return an integer."""
        from PIL import Image
        # Create a simple test image
        img = Image.new('L', (100, 100), 128)
        result = self.proc._otsu_threshold(img)
        assert isinstance(result, int)
        assert 0 <= result <= 255

    def test_bimodal_image(self):
        """Image with two distinct pixel groups should find threshold between them."""
        from PIL import Image
        import random
        random.seed(42)
        img = Image.new('L', (100, 100))
        # Dark group (~50) and light group (~200) with some noise
        for x in range(100):
            for y in range(100):
                if x < 50:
                    img.putpixel((x, y), random.randint(30, 70))
                else:
                    img.putpixel((x, y), random.randint(180, 220))
        threshold = self.proc._otsu_threshold(img)
        # Threshold should be between the two groups
        assert 70 <= threshold < 180
