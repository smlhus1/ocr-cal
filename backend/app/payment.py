"""
Payment and subscription management with Stripe.
Handles free tier quota and premium subscriptions.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import stripe
from sqlalchemy import select, func

from app.config import settings
from app.database import AsyncSessionLocal, UploadAnalytics

logger = logging.getLogger('shiftsync')


# Initialize Stripe
if settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key


class PaymentService:
    """Service for managing payments and subscriptions."""
    
    # Pricing
    FREE_TIER_LIMIT = 2  # uploads per month
    PREMIUM_PRICE_NOK = 99_00  # 99 NOK in øre
    
    def __init__(self):
        """Initialize payment service."""
        if not settings.stripe_secret_key:
            logger.warning("Stripe not configured. Payment features will be disabled.")
    
    async def check_quota(self, user_identifier: str) -> tuple[bool, int]:
        """
        Check if user has remaining quota this month.
        
        Args:
            user_identifier: Hashed user identifier (from IP)
            
        Returns:
            Tuple of (has_quota, remaining_uploads)
        """
        # Get upload count for this month
        count = await self._get_upload_count_this_month(user_identifier)
        
        remaining = max(0, self.FREE_TIER_LIMIT - count)
        has_quota = remaining > 0
        
        return has_quota, remaining
    
    async def _get_upload_count_this_month(self, user_identifier: str) -> int:
        """Get number of uploads this month for user."""
        # Start of current month
        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1)
        
        async with AsyncSessionLocal() as session:
            # Note: We don't store user_identifier in database for privacy
            # For MVP, we use simple rate limiting per IP
            # In production, implement proper user accounts with auth
            
            # For now, return 0 (unlimited) since we don't track users
            # TODO: Implement proper user tracking with auth
            return 0
    
    async def create_checkout_session(
        self,
        success_url: str,
        cancel_url: str,
        customer_email: Optional[str] = None
    ) -> str:
        """
        Create Stripe Checkout session for subscription.
        
        Args:
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if user cancels
            customer_email: Optional customer email
            
        Returns:
            Checkout session URL
        """
        if not stripe.api_key:
            raise ValueError("Stripe not configured")
        
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'nok',
                        'product_data': {
                            'name': 'ShiftSync Premium',
                            'description': 'Ubegrensede vaktplan-konverteringer per måned',
                        },
                        'unit_amount': self.PREMIUM_PRICE_NOK,
                        'recurring': {
                            'interval': 'month',
                        },
                    },
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                allow_promotion_codes=True,
            )
            
            return session.url
            
        except stripe.error.StripeError as e:
            raise ValueError(f"Stripe error: {str(e)}")
    
    async def verify_subscription(self, session_id: str) -> bool:
        """
        Verify that a checkout session was successful.
        
        Args:
            session_id: Stripe checkout session ID
            
        Returns:
            True if subscription is active
        """
        if not stripe.api_key:
            return False
        
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            
            if session.payment_status == 'paid' and session.subscription:
                # Subscription is active
                return True
            
            return False
            
        except stripe.error.StripeError:
            return False
    
    async def cancel_subscription(self, subscription_id: str) -> bool:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            
        Returns:
            True if cancelled successfully
        """
        if not stripe.api_key:
            return False
        
        try:
            stripe.Subscription.delete(subscription_id)
            return True
        except stripe.error.StripeError:
            return False


# Singleton instance
payment_service = PaymentService()

