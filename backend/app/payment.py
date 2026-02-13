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
    """Service for managing payments and credit purchases."""

    # Free tier
    FREE_TIER_LIMIT = 2  # uploads per month

    # Credit packs (one-time purchases)
    CREDIT_PACKS = {
        "pack_5": {
            "credits": 5,
            "price_nok": 39_00,  # 39 NOK in øre
            "name": "5-pack",
            "price_per_credit": 7_80,
        },
        "pack_15": {
            "credits": 15,
            "price_nok": 89_00,  # 89 NOK in øre
            "name": "15-pack",
            "price_per_credit": 5_93,
        },
        "pack_50": {
            "credits": 50,
            "price_nok": 249_00,  # 249 NOK in øre
            "name": "50-pack",
            "price_per_credit": 4_98,
        },
    }

    # Legacy
    PREMIUM_PRICE_NOK = 99_00  # 99 NOK in øre

    def __init__(self):
        """Initialize payment service."""
        if not settings.stripe_secret_key:
            logger.warning("Stripe not configured. Payment features will be disabled.")
    
    async def check_quota(self, session_id: str) -> tuple[bool, int, int]:
        """
        Check if session has remaining quota.

        Priority order:
        1. Legacy premium subscribers → unlimited
        2. Free quota this month < 2 → allow (Tesseract OCR)
        3. Credits > 0 → allow (AI OCR, deduct on use)
        4. No quota → deny

        Args:
            session_id: Anonymous session cookie ID

        Returns:
            Tuple of (has_quota, free_remaining, credits)
            free_remaining=-1 means unlimited (legacy premium)
        """
        # Skip quota check in development
        if settings.environment == "development":
            return True, -1, 0

        from app.database import get_session, get_upload_count_this_month, get_credit_balance

        # Check session record
        session_record = await get_session(session_id)

        # 1. Legacy premium subscriber → unlimited
        if session_record and session_record.status == 'premium':
            return True, -1, session_record.credits if session_record else 0

        # 2. Count free uploads this month
        count = await get_upload_count_this_month(session_id)
        free_remaining = max(0, self.FREE_TIER_LIMIT - count)

        # Get credit balance
        credits = session_record.credits if session_record else 0

        if free_remaining > 0:
            return True, free_remaining, credits

        # 3. Has paid credits
        if credits > 0:
            return True, 0, credits

        # 4. No quota
        return False, 0, credits
    
    async def create_checkout_session(
        self,
        success_url: str,
        cancel_url: str,
        customer_email: Optional[str] = None,
        client_reference_id: Optional[str] = None
    ) -> str:
        """
        Create Stripe Checkout session for subscription.

        Args:
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if user cancels
            customer_email: Optional customer email
            client_reference_id: Session cookie ID for linking payment to session

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
                client_reference_id=client_reference_id,
                allow_promotion_codes=True,
            )
            
            return session.url
            
        except stripe.error.StripeError as e:
            raise ValueError(f"Stripe error: {str(e)}")
    
    async def create_credit_checkout_session(
        self,
        pack_id: str,
        success_url: str,
        cancel_url: str,
        client_reference_id: Optional[str] = None
    ) -> str:
        """
        Create Stripe Checkout session for one-time credit purchase.

        Args:
            pack_id: Credit pack identifier (pack_5, pack_15, pack_50)
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if user cancels
            client_reference_id: Session cookie ID for linking payment to session

        Returns:
            Checkout session URL
        """
        if not stripe.api_key:
            raise ValueError("Stripe not configured")

        pack = self.CREDIT_PACKS.get(pack_id)
        if not pack:
            raise ValueError(f"Invalid pack_id: {pack_id}")

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'nok',
                        'product_data': {
                            'name': f'ShiftSync {pack["name"]}',
                            'description': f'{pack["credits"]} konverteringer med AI OCR',
                        },
                        'unit_amount': pack['price_nok'],
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=client_reference_id,
                metadata={
                    'pack_id': pack_id,
                    'credits': str(pack['credits']),
                },
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

