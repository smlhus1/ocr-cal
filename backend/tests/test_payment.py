"""
Tests for payment endpoint - open redirect prevention.
"""
import pytest
from pydantic import ValidationError
from app.api.payment import CreateCheckoutRequest


class TestCheckoutURLValidation:
    """Tests for checkout URL validation against open redirect."""

    def test_valid_localhost_url(self):
        req = CreateCheckoutRequest(
            success_url="http://localhost:3000/success",
            cancel_url="http://localhost:3000/cancel"
        )
        assert req.success_url == "http://localhost:3000/success"

    def test_valid_production_url(self):
        req = CreateCheckoutRequest(
            success_url="https://shiftsync.no/success",
            cancel_url="https://shiftsync.no/cancel"
        )
        assert req.success_url == "https://shiftsync.no/success"

    def test_rejects_evil_domain(self):
        with pytest.raises(ValidationError):
            CreateCheckoutRequest(
                success_url="https://evil.com/steal",
                cancel_url="https://shiftsync.no/cancel"
            )

    def test_rejects_evil_cancel_url(self):
        with pytest.raises(ValidationError):
            CreateCheckoutRequest(
                success_url="https://shiftsync.no/success",
                cancel_url="https://evil.com/phish"
            )

    def test_rejects_javascript_url(self):
        with pytest.raises(ValidationError):
            CreateCheckoutRequest(
                success_url="javascript:alert(1)",
                cancel_url="https://shiftsync.no/cancel"
            )

    def test_rejects_ftp_scheme(self):
        with pytest.raises(ValidationError):
            CreateCheckoutRequest(
                success_url="ftp://evil.com/file",
                cancel_url="https://shiftsync.no/cancel"
            )
