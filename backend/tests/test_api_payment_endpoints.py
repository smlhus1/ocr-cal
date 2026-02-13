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


class TestCreditStatus:
    """Tests for GET /api/payment/credit-status."""

    @patch('app.api.payment.payment_service')
    def test_credit_status_free(self, mock_service, client):
        mock_service.check_quota = AsyncMock(return_value=(True, 2, 0))
        mock_service.FREE_TIER_LIMIT = 2
        mock_service.CREDIT_PACKS = {
            "pack_5": {"credits": 5, "price_nok": 39_00, "name": "5-pack", "price_per_credit": 7_80},
        }

        response = client.get("/api/payment/credit-status")
        assert response.status_code == 200
        data = response.json()
        assert data["has_quota"] is True
        assert data["free_remaining"] == 2
        assert data["credits"] == 0
        assert data["free_tier_limit"] == 2
        assert len(data["credit_packs"]) == 1

    @patch('app.api.payment.payment_service')
    def test_credit_status_premium(self, mock_service, client):
        mock_service.check_quota = AsyncMock(return_value=(True, -1, 0))
        mock_service.FREE_TIER_LIMIT = 2
        mock_service.CREDIT_PACKS = {}

        response = client.get("/api/payment/credit-status")
        assert response.status_code == 200
        data = response.json()
        assert data["has_quota"] is True
        assert data["free_remaining"] == -1

    @patch('app.api.payment.payment_service')
    def test_credit_status_with_credits(self, mock_service, client):
        mock_service.check_quota = AsyncMock(return_value=(True, 0, 10))
        mock_service.FREE_TIER_LIMIT = 2
        mock_service.CREDIT_PACKS = {}

        response = client.get("/api/payment/credit-status")
        assert response.status_code == 200
        data = response.json()
        assert data["has_quota"] is True
        assert data["free_remaining"] == 0
        assert data["credits"] == 10


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


class TestCreditCheckoutEndpoint:
    """Tests for POST /api/payment/create-credit-checkout."""

    def test_rejects_invalid_pack_id(self, client):
        response = client.post("/api/payment/create-credit-checkout", json={
            "pack_id": "invalid_pack",
            "success_url": "http://localhost:3000/success",
            "cancel_url": "http://localhost:3000/cancel",
        })
        assert response.status_code == 422

    def test_rejects_invalid_redirect_host(self, client):
        response = client.post("/api/payment/create-credit-checkout", json={
            "pack_id": "pack_5",
            "success_url": "https://evil.com/steal",
            "cancel_url": "https://evil.com/cancel",
        })
        assert response.status_code == 422
