"""
Payment-related endpoints for Stripe integration.
"""
import logging
import re
from urllib.parse import urlparse

import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from app.config import settings
from app.payment import payment_service

logger = logging.getLogger('shiftsync')

router = APIRouter()

# Allowed hostnames for redirect URLs
ALLOWED_REDIRECT_HOSTS = {
    "shiftsync.no",
    "www.shiftsync.no",
    "localhost",
    "127.0.0.1",
}


class CreateCheckoutRequest(BaseModel):
    """Request to create checkout session."""
    success_url: str
    cancel_url: str
    customer_email: str | None = None

    @field_validator('success_url', 'cancel_url')
    @classmethod
    def validate_redirect_url(cls, v: str) -> str:
        """Validate that redirect URLs point to allowed hosts to prevent open redirect."""
        try:
            parsed = urlparse(v)
            hostname = parsed.hostname or ""
            if hostname not in ALLOWED_REDIRECT_HOSTS:
                raise ValueError(f"Redirect URL host not allowed: {hostname}")
            if parsed.scheme not in ("http", "https"):
                raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
        except ValueError:
            raise
        except Exception:
            raise ValueError("Invalid redirect URL")
        return v


class CheckoutResponse(BaseModel):
    """Response with checkout URL."""
    checkout_url: str


@router.post("/create-checkout-session", response_model=CheckoutResponse)
async def create_checkout_session(request: CreateCheckoutRequest):
    """
    Create Stripe checkout session for premium subscription.
    """
    try:
        checkout_url = await payment_service.create_checkout_session(
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            customer_email=request.customer_email
        )

        return CheckoutResponse(checkout_url=checkout_url)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Checkout session creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Webhook endpoint for Stripe events.

    Verifies webhook signature before processing.
    """
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    webhook_secret = settings.stripe_webhook_secret

    if not webhook_secret:
        logger.error("Stripe webhook secret not configured")
        raise HTTPException(status_code=503, detail="Webhook not configured")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    # Verify webhook signature
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        raise HTTPException(status_code=400, detail="Webhook verification failed")

    # Handle events
    event_type = event.get("type", "")
    logger.info(f"Stripe webhook received: {event_type}")

    if event_type == "checkout.session.completed":
        logger.info("Checkout session completed")
    elif event_type == "customer.subscription.deleted":
        logger.info("Subscription cancelled")
    elif event_type == "invoice.payment_failed":
        logger.warning("Invoice payment failed")

    return {"status": "success"}


@router.get("/subscription-status/{user_id}")
async def get_subscription_status(user_id: str):
    """
    Get subscription status for user.
    """
    has_quota, remaining = await payment_service.check_quota(user_id)

    return {
        "has_quota": has_quota,
        "remaining_uploads": remaining,
        "free_tier_limit": payment_service.FREE_TIER_LIMIT,
        "premium_price_nok": payment_service.PREMIUM_PRICE_NOK / 100
    }
