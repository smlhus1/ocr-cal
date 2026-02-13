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
from app.security import limiter

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
@limiter.limit("5/minute")
async def create_checkout_session(request: Request, checkout_request: CreateCheckoutRequest):
    """
    Create Stripe checkout session for premium subscription.
    Passes session_id as client_reference_id so webhooks can link payment to session.
    """
    session_id = getattr(request.state, 'session_id', None)
    if not session_id:
        session_id = request.cookies.get('session_id')

    try:
        checkout_url = await payment_service.create_checkout_session(
            success_url=checkout_request.success_url,
            cancel_url=checkout_request.cancel_url,
            customer_email=checkout_request.customer_email,
            client_reference_id=session_id
        )

        return CheckoutResponse(checkout_url=checkout_url)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Checkout session creation failed: %s", e)
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
        logger.error("Stripe webhook error: %s", e)
        raise HTTPException(status_code=400, detail="Webhook verification failed")

    # Handle events
    event_type = event.get("type", "")
    logger.info("Stripe webhook received: %s", event_type)

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(event)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(event)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(event)

    return {"status": "success"}


async def _handle_checkout_completed(event: dict) -> None:
    """Handle successful checkout - activate premium for session."""
    from app.database import upsert_session

    session_data = event.get("data", {}).get("object", {})
    subscription_id = session_data.get("subscription")
    # client_reference_id should contain the session_id cookie value
    client_session_id = session_data.get("client_reference_id")

    if client_session_id and subscription_id:
        await upsert_session(
            session_id=client_session_id,
            stripe_subscription_id=subscription_id,
            status='premium'
        )
        logger.info("Premium activated for session %s", client_session_id[:8])
    else:
        logger.warning(
            "Checkout completed but missing session data: client_ref=%s, sub=%s",
            client_session_id, subscription_id
        )


async def _handle_subscription_deleted(event: dict) -> None:
    """Handle subscription cancellation."""
    from app.database import AsyncSessionLocal, AnonymousSession

    sub_data = event.get("data", {}).get("object", {})
    subscription_id = sub_data.get("id")

    if not subscription_id:
        return

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, update
        stmt = update(AnonymousSession).where(
            AnonymousSession.stripe_subscription_id == subscription_id
        ).values(status='cancelled')
        await session.execute(stmt)
        await session.commit()

    logger.info("Subscription %s cancelled", subscription_id)


async def _handle_payment_failed(event: dict) -> None:
    """Handle failed payment - log warning."""
    sub_data = event.get("data", {}).get("object", {})
    subscription_id = sub_data.get("subscription")
    logger.warning("Payment failed for subscription %s", subscription_id)


@router.get("/subscription-status")
@limiter.limit("10/minute")
async def get_subscription_status(request: Request):
    """
    Get subscription status for current session.
    Session is identified from session cookie.
    """
    session_id = getattr(request.state, 'session_id', None)
    if not session_id:
        session_id = request.cookies.get('session_id', 'unknown')
    has_quota, remaining = await payment_service.check_quota(session_id)

    return {
        "has_quota": has_quota,
        "remaining_uploads": remaining,
        "free_tier_limit": payment_service.FREE_TIER_LIMIT,
        "premium_price_nok": payment_service.PREMIUM_PRICE_NOK / 100
    }
