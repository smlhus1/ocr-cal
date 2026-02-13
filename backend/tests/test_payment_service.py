"""
Tests for PaymentService quota logic and checkout session creation.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.payment import PaymentService


class TestCheckQuota:
    """Tests for PaymentService.check_quota()."""

    @pytest.mark.asyncio
    @patch('app.database.get_upload_count_this_month', new_callable=AsyncMock)
    @patch('app.database.get_session', new_callable=AsyncMock)
    async def test_premium_user_unlimited(self, mock_get_session, mock_count):
        service = PaymentService()

        mock_session = MagicMock()
        mock_session.status = 'premium'
        mock_get_session.return_value = mock_session

        has_quota, remaining = await service.check_quota("session-123")
        assert has_quota is True
        assert remaining == -1  # Unlimited

    @pytest.mark.asyncio
    @patch('app.database.get_upload_count_this_month', new_callable=AsyncMock)
    @patch('app.database.get_session', new_callable=AsyncMock)
    async def test_free_user_with_quota(self, mock_get_session, mock_count):
        service = PaymentService()

        mock_get_session.return_value = None  # No session record
        mock_count.return_value = 0

        has_quota, remaining = await service.check_quota("session-123")
        assert has_quota is True
        assert remaining == 2

    @pytest.mark.asyncio
    @patch('app.database.get_upload_count_this_month', new_callable=AsyncMock)
    @patch('app.database.get_session', new_callable=AsyncMock)
    async def test_free_user_one_used(self, mock_get_session, mock_count):
        service = PaymentService()

        mock_get_session.return_value = None
        mock_count.return_value = 1

        has_quota, remaining = await service.check_quota("session-123")
        assert has_quota is True
        assert remaining == 1

    @pytest.mark.asyncio
    @patch('app.database.get_upload_count_this_month', new_callable=AsyncMock)
    @patch('app.database.get_session', new_callable=AsyncMock)
    async def test_free_user_quota_exceeded(self, mock_get_session, mock_count):
        service = PaymentService()

        mock_get_session.return_value = None
        mock_count.return_value = 2

        has_quota, remaining = await service.check_quota("session-123")
        assert has_quota is False
        assert remaining == 0

    @pytest.mark.asyncio
    @patch('app.database.get_upload_count_this_month', new_callable=AsyncMock)
    @patch('app.database.get_session', new_callable=AsyncMock)
    async def test_free_user_over_limit(self, mock_get_session, mock_count):
        service = PaymentService()

        mock_get_session.return_value = None
        mock_count.return_value = 5  # Way over limit

        has_quota, remaining = await service.check_quota("session-123")
        assert has_quota is False
        assert remaining == 0

    @pytest.mark.asyncio
    @patch('app.database.get_upload_count_this_month', new_callable=AsyncMock)
    @patch('app.database.get_session', new_callable=AsyncMock)
    async def test_no_session_record(self, mock_get_session, mock_count):
        service = PaymentService()

        mock_get_session.return_value = None
        mock_count.return_value = 0

        has_quota, remaining = await service.check_quota("new-session")
        assert has_quota is True
        assert remaining == 2

    @pytest.mark.asyncio
    @patch('app.database.get_upload_count_this_month', new_callable=AsyncMock)
    @patch('app.database.get_session', new_callable=AsyncMock)
    async def test_cancelled_gets_free_tier(self, mock_get_session, mock_count):
        service = PaymentService()

        mock_session = MagicMock()
        mock_session.status = 'cancelled'
        mock_get_session.return_value = mock_session
        mock_count.return_value = 1

        has_quota, remaining = await service.check_quota("session-123")
        assert has_quota is True
        assert remaining == 1  # Falls back to free tier


class TestCreateCheckoutSession:
    """Tests for PaymentService.create_checkout_session()."""

    @pytest.mark.asyncio
    async def test_no_stripe_key_raises(self):
        service = PaymentService()

        with patch('app.payment.stripe') as mock_stripe:
            mock_stripe.api_key = None

            with pytest.raises(ValueError, match="Stripe not configured"):
                await service.create_checkout_session(
                    success_url="https://shiftsync.no/success",
                    cancel_url="https://shiftsync.no/cancel",
                )

    @pytest.mark.asyncio
    async def test_calls_stripe_correctly(self):
        service = PaymentService()

        with patch('app.payment.stripe') as mock_stripe:
            mock_stripe.api_key = "sk_test_123"
            mock_session = MagicMock()
            mock_session.url = "https://checkout.stripe.com/session/123"
            mock_stripe.checkout.Session.create.return_value = mock_session

            url = await service.create_checkout_session(
                success_url="https://shiftsync.no/success",
                cancel_url="https://shiftsync.no/cancel",
                customer_email="test@example.com",
                client_reference_id="session-abc",
            )

            assert url == "https://checkout.stripe.com/session/123"
            mock_stripe.checkout.Session.create.assert_called_once()
            call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
            assert call_kwargs['mode'] == 'subscription'
            assert call_kwargs['customer_email'] == "test@example.com"
            assert call_kwargs['client_reference_id'] == "session-abc"

    @pytest.mark.asyncio
    async def test_stripe_error_wrapped(self):
        service = PaymentService()

        with patch('app.payment.stripe') as mock_stripe:
            mock_stripe.api_key = "sk_test_123"
            mock_stripe.error.StripeError = Exception
            mock_stripe.checkout.Session.create.side_effect = Exception("API error")

            with pytest.raises(ValueError, match="Stripe error"):
                await service.create_checkout_session(
                    success_url="https://shiftsync.no/success",
                    cancel_url="https://shiftsync.no/cancel",
                )
