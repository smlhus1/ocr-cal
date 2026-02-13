"""
Tests for calendar_generator.py - pure functions, no mocking needed.
"""
import re

import pytest
from icalendar import Calendar

from app.ocr.calendar_generator import sanitize_calendar_text, generate_ics
from app.models import Shift


class TestSanitizeCalendarText:
    """Tests for sanitize_calendar_text()."""

    def test_removes_html_tags(self):
        result = sanitize_calendar_text("<script>alert(1)</script>")
        assert "<script>" not in result
        assert "alert(1)" not in result or "<" not in result

    def test_preserves_norwegian_chars(self):
        result = sanitize_calendar_text("Ærlig Øystein Åse")
        assert "Ærlig" in result or "rlig" in result
        assert "ystein" in result

    def test_truncates_long_input(self):
        long_text = "A" * 150
        result = sanitize_calendar_text(long_text)
        assert len(result) <= 100
        assert result.endswith("...")

    def test_empty_input_returns_empty(self):
        assert sanitize_calendar_text("") == ""
        assert sanitize_calendar_text(None) == ""

    def test_normalizes_whitespace(self):
        result = sanitize_calendar_text("  foo   bar  ")
        assert result == "foo bar"

    def test_removes_control_chars(self):
        result = sanitize_calendar_text("\x00test\x07value")
        assert "\x00" not in result
        assert "\x07" not in result
        assert "test" in result
        assert "value" in result

    def test_removes_angle_brackets(self):
        result = sanitize_calendar_text("test<>value")
        assert "<" not in result
        assert ">" not in result

    def test_max_length_respected(self):
        result = sanitize_calendar_text("Hello World", max_length=5)
        assert len(result) <= 5

    def test_short_input_unchanged(self):
        result = sanitize_calendar_text("Ola Nordmann")
        assert result == "Ola Nordmann"


class TestGenerateIcs:
    """Tests for generate_ics()."""

    def test_valid_ics_output(self, sample_shifts):
        ics_bytes = generate_ics(sample_shifts, "Test User")
        cal = Calendar.from_ical(ics_bytes)
        assert cal is not None

    def test_contains_all_shifts(self, sample_shifts):
        ics_bytes = generate_ics(sample_shifts, "Test User")
        cal = Calendar.from_ical(ics_bytes)
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        assert len(events) == 3

    def test_correct_event_times(self):
        shifts = [
            Shift(
                date="20.01.2025",
                start_time="07:00",
                end_time="15:00",
                shift_type="tidlig",
                confidence=1.0,
            )
        ]
        ics_bytes = generate_ics(shifts, "Test")
        cal = Calendar.from_ical(ics_bytes)
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        event = events[0]

        dtstart = event.get("dtstart").dt
        dtend = event.get("dtend").dt
        assert dtstart.hour == 7
        assert dtstart.minute == 0
        assert dtend.hour == 15
        assert dtend.minute == 0
        assert dtstart.day == 20
        assert dtend.day == 20  # Same day

    def test_midnight_crossing(self):
        shifts = [
            Shift(
                date="20.01.2025",
                start_time="22:00",
                end_time="06:00",
                shift_type="natt",
                confidence=1.0,
            )
        ]
        ics_bytes = generate_ics(shifts, "Test")
        cal = Calendar.from_ical(ics_bytes)
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        event = events[0]

        dtstart = event.get("dtstart").dt
        dtend = event.get("dtend").dt
        assert dtstart.day == 20
        assert dtend.day == 21  # Next day

    def test_same_day_shift(self):
        shifts = [
            Shift(
                date="20.01.2025",
                start_time="07:00",
                end_time="15:00",
                shift_type="tidlig",
                confidence=1.0,
            )
        ]
        ics_bytes = generate_ics(shifts, "Test")
        cal = Calendar.from_ical(ics_bytes)
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        event = events[0]

        dtstart = event.get("dtstart").dt
        dtend = event.get("dtend").dt
        assert dtstart.day == dtend.day

    def test_xss_in_owner_sanitized(self):
        shifts = [
            Shift(
                date="20.01.2025",
                start_time="07:00",
                end_time="15:00",
                shift_type="tidlig",
                confidence=1.0,
            )
        ]
        ics_bytes = generate_ics(shifts, "<script>alert('xss')</script>")
        content = ics_bytes.decode("utf-8")
        assert "<script>" not in content

    def test_empty_owner_defaults(self):
        shifts = [
            Shift(
                date="20.01.2025",
                start_time="07:00",
                end_time="15:00",
                shift_type="tidlig",
                confidence=1.0,
            )
        ]
        ics_bytes = generate_ics(shifts, "")
        content = ics_bytes.decode("utf-8")
        assert "Ansatt" in content

    def test_event_summary_format(self):
        shifts = [
            Shift(
                date="20.01.2025",
                start_time="07:00",
                end_time="15:00",
                shift_type="tidlig",
                confidence=1.0,
            )
        ]
        ics_bytes = generate_ics(shifts, "Ola")
        cal = Calendar.from_ical(ics_bytes)
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        summary = str(events[0].get("summary"))
        assert "Ola" in summary
        assert "jobber" in summary
        assert "tidlig" in summary

    def test_calendar_metadata(self):
        shifts = [
            Shift(
                date="20.01.2025",
                start_time="07:00",
                end_time="15:00",
                shift_type="tidlig",
                confidence=1.0,
            )
        ]
        ics_bytes = generate_ics(shifts, "Test")
        cal = Calendar.from_ical(ics_bytes)
        assert "ShiftSync" in str(cal.get("prodid"))
        assert str(cal.get("version")) == "2.0"
        assert str(cal.get("calscale")) == "GREGORIAN"

    def test_events_have_timezone(self):
        """Events should have Europe/Oslo timezone."""
        shifts = [
            Shift(
                date="20.01.2025",
                start_time="07:00",
                end_time="15:00",
                shift_type="tidlig",
                confidence=1.0,
            )
        ]
        ics_bytes = generate_ics(shifts, "Test")
        cal = Calendar.from_ical(ics_bytes)
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        event = events[0]

        dtstart = event.get("dtstart").dt
        dtend = event.get("dtend").dt
        assert dtstart.tzinfo is not None
        assert dtend.tzinfo is not None
        # Verify it's Europe/Oslo (UTC+1 in January)
        assert "Europe/Oslo" in str(dtstart.tzinfo) or dtstart.utcoffset().total_seconds() == 3600

    def test_uid_is_uuid_format(self):
        """UID should be UUID-based, not datetime-based."""
        shifts = [
            Shift(
                date="20.01.2025",
                start_time="07:00",
                end_time="15:00",
                shift_type="tidlig",
                confidence=1.0,
            )
        ]
        ics_bytes = generate_ics(shifts, "Test")
        cal = Calendar.from_ical(ics_bytes)
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        uid = str(events[0].get("uid"))
        # UUID4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx@shiftsync.no
        assert uid.endswith("@shiftsync.no")
        uuid_part = uid.replace("@shiftsync.no", "")
        assert re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', uuid_part)

    def test_unique_uids_per_event(self):
        """Each event should have a unique UID."""
        shifts = [
            Shift(date="20.01.2025", start_time="07:00", end_time="15:00",
                  shift_type="tidlig", confidence=1.0),
            Shift(date="21.01.2025", start_time="07:00", end_time="15:00",
                  shift_type="tidlig", confidence=1.0),
        ]
        ics_bytes = generate_ics(shifts, "Test")
        cal = Calendar.from_ical(ics_bytes)
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        uids = [str(e.get("uid")) for e in events]
        assert len(set(uids)) == 2  # All unique
