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


def _validate_redirect_url(v: str) -> str:
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


class CreateCheckoutRequest(BaseModel):
    """Request to create legacy subscription checkout session."""
    success_url: str
    cancel_url: str
    customer_email: str | None = None

    @field_validator('success_url', 'cancel_url')
    @classmethod
    def validate_redirect_url(cls, v: str) -> str:
        return _validate_redirect_url(v)


class CreateCreditCheckoutRequest(BaseModel):
    """Request to create credit pack checkout session."""
    pack_id: str
    success_url: str
    cancel_url: str

    @field_validator('pack_id')
    @classmethod
    def validate_pack_id(cls, v: str) -> str:
        if v not in payment_service.CREDIT_PACKS:
            raise ValueError(f"Invalid pack_id. Must be one of: {', '.join(payment_service.CREDIT_PACKS.keys())}")
        return v

    @field_validator('success_url', 'cancel_url')
    @classmethod
    def validate_redirect_url(cls, v: str) -> str:
        return _validate_redirect_url(v)


class CheckoutResponse(BaseModel):
    """Response with checkout URL."""
    checkout_url: str


@router.post("/create-checkout-session", response_model=CheckoutResponse)
@limiter.limit("5/minute")
async def create_checkout_session(request: Request, checkout_request: CreateCheckoutRequest):
    """
    Create Stripe checkout session for legacy premium subscription.
    Kept for backward compatibility.
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


@router.post("/create-credit-checkout", response_model=CheckoutResponse)
@limiter.limit("5/minute")
async def create_credit_checkout(request: Request, checkout_request: CreateCreditCheckoutRequest):
    """
    Create Stripe checkout session for one-time credit purchase.
    """
    session_id = getattr(request.state, 'session_id', None)
    if not session_id:
        session_id = request.cookies.get('session_id')

    try:
        checkout_url = await payment_service.create_credit_checkout_session(
            pack_id=checkout_request.pack_id,
            success_url=checkout_request.success_url,
            cancel_url=checkout_request.cancel_url,
            client_reference_id=session_id,
        )

        return CheckoutResponse(checkout_url=checkout_url)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Credit checkout creation failed: %s", e)
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
    """Handle successful checkout - credit purchase or legacy subscription."""
    session_data = event.get("data", {}).get("object", {})
    client_session_id = session_data.get("client_reference_id")
    metadata = session_data.get("metadata", {})

    if not client_session_id:
        logger.warning("Checkout completed but missing client_reference_id")
        return

    # Credit pack purchase (one-time payment with metadata)
    pack_id = metadata.get("pack_id")
    if pack_id:
        credits_str = metadata.get("credits")
        if not credits_str:
            logger.error("Credit checkout missing credits in metadata: pack_id=%s", pack_id)
            return

        from app.database import add_credits
        credits = int(credits_str)
        await add_credits(client_session_id, credits)
        logger.info(
            "Added %d credits for session %s (pack: %s)",
            credits, client_session_id[:8], pack_id
        )
        return

    # Legacy subscription checkout
    subscription_id = session_data.get("subscription")
    if subscription_id:
        from app.database import upsert_session
        await upsert_session(
            session_id=client_session_id,
            stripe_subscription_id=subscription_id,
            status='premium'
        )
        logger.info("Premium activated for session %s", client_session_id[:8])
    else:
        logger.warning(
            "Checkout completed but no pack_id or subscription: client_ref=%s",
            client_session_id[:8]
        )


async def _handle_subscription_deleted(event: dict) -> None:
    """Handle subscription cancellation (legacy)."""
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
    """Handle failed payment - log warning (legacy)."""
    sub_data = event.get("data", {}).get("object", {})
    subscription_id = sub_data.get("subscription")
    logger.warning("Payment failed for subscription %s", subscription_id)


@router.get("/credit-status")
@limiter.limit("10/minute")
async def get_credit_status(request: Request):
    """
    Get credit and quota status for current session.
    Session is identified from session cookie.
    """
    session_id = getattr(request.state, 'session_id', None)
    if not session_id:
        session_id = request.cookies.get('session_id', 'unknown')

    has_quota, free_remaining, credits = await payment_service.check_quota(session_id)

    # Build credit packs info for frontend
    credit_packs = [
        {
            "pack_id": pack_id,
            "credits": pack["credits"],
            "price_nok": pack["price_nok"] / 100,
            "name": pack["name"],
            "price_per_credit": pack["price_per_credit"] / 100,
        }
        for pack_id, pack in payment_service.CREDIT_PACKS.items()
    ]

    return {
        "has_quota": has_quota,
        "free_remaining": free_remaining,
        "credits": credits,
        "free_tier_limit": payment_service.FREE_TIER_LIMIT,
        "credit_packs": credit_packs,
    }
