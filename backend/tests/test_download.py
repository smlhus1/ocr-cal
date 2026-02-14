"""
Tests for download endpoint - header injection and IDOR.
"""
import re
from app.api.download import sanitize_filename


class TestSanitizeFilename:
    """Tests for filename sanitization."""

    def test_normal_name(self):
        assert sanitize_filename("Ola Nordmann") == "Ola_Nordmann"

    def test_special_characters(self):
        result = sanitize_filename("name\r\nContent-Type: text/html")
        assert "\r" not in result
        assert "\n" not in result
        # CRLF and special chars are replaced, but alphanumeric text is kept
        assert ":" not in result

    def test_max_length(self):
        long_name = "A" * 100
        result = sanitize_filename(long_name)
        assert len(result) <= 50

    def test_unicode_characters(self):
        result = sanitize_filename("Ola <script>alert(1)</script>")
        assert "<" not in result
        assert ">" not in result

    def test_empty_string(self):
        result = sanitize_filename("")
        assert result == ""

    def test_header_injection(self):
        """Verify CRLF injection in filename is prevented."""
        result = sanitize_filename("file\r\nX-Evil: header")
        assert "\r" not in result
        assert "\n" not in result
