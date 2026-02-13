"""
Tests for payment API endpoints.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

import stripe


class TestWebhookEndpoint:
    """Tests for POST /api/payment/webhook."""

    @patch('app.api.payment.settings')
    def test_webhook_missing_signature(self, mock_settings, client):
        mock_settings.stripe_webhook_secret = "whsec_test123"

        response = client.post(
            "/api/payment/webhook",
            content=b'{"type": "test"}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400

    @patch('app.api.payment.stripe.Webhook.construct_event',
           side_effect=stripe.error.SignatureVerificationError("bad sig", "header"))
    @patch('app.api.payment.settings')
    def test_webhook_invalid_signature(self, mock_settings, mock_construct, client):
        mock_settings.stripe_webhook_secret = "whsec_test123"

        response = client.post(
            "/api/payment/webhook",
            content=b'{"type": "test"}',
            headers={
                "Content-Type": "application/json",
                "stripe-signature": "t=123,v1=bad",
            },
        )
        assert response.status_code == 400


class TestSubscriptionStatus:
    """Tests for GET /api/payment/subscription-status."""

    @patch('app.api.payment.payment_service')
    def test_subscription_status_free(self, mock_service, client):
        mock_service.check_quota = AsyncMock(return_value=(True, 2))
        mock_service.FREE_TIER_LIMIT = 2
        mock_service.PREMIUM_PRICE_NOK = 99_00

        response = client.get("/api/payment/subscription-status")
        assert response.status_code == 200
        data = response.json()
        assert data["has_quota"] is True
        assert data["remaining_uploads"] == 2
        assert data["free_tier_limit"] == 2

    @patch('app.api.payment.payment_service')
    def test_subscription_status_premium(self, mock_service, client):
        mock_service.check_quota = AsyncMock(return_value=(True, -1))
        mock_service.FREE_TIER_LIMIT = 2
        mock_service.PREMIUM_PRICE_NOK = 99_00

        response = client.get("/api/payment/subscription-status")
        assert response.status_code == 200
        data = response.json()
        assert data["has_quota"] is True
        assert data["remaining_uploads"] == -1


class TestCheckoutEndpoint:
    """Tests for POST /api/payment/create-checkout-session."""

    def test_rejects_invalid_redirect_host(self, client):
        response = client.post("/api/payment/create-checkout-session", json={
            "success_url": "https://evil.com/steal",
            "cancel_url": "https://evil.com/cancel",
        })
        assert response.status_code == 422  # Pydantic validation

    def test_accepts_allowed_host(self, client):
        response = client.post("/api/payment/create-checkout-session", json={
            "success_url": "https://shiftsync.no/success",
            "cancel_url": "https://shiftsync.no/cancel",
        })
        # May fail if Stripe not configured, but should not be 422
        assert response.status_code != 422

    def test_accepts_localhost(self, client):
        response = client.post("/api/payment/create-checkout-session", json={
            "success_url": "http://localhost:3000/success",
            "cancel_url": "http://localhost:3000/cancel",
        })
        assert response.status_code != 422
