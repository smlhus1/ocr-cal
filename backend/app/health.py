"""
Health check endpoints for monitoring and load balancer probes.
"""
import logging
from datetime import datetime, timezone

import pytesseract
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.config import settings
from app.database import AsyncSessionLocal

logger = logging.getLogger('shiftsync')

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    Returns 200 if service is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.environment
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with dependency verification.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {}
    }

    # Check database
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        logger.warning(f"Health check database failed: {e}")
        health_status["checks"]["database"] = "unhealthy"
        health_status["status"] = "degraded"

    # Check Tesseract
    try:
        version = pytesseract.get_tesseract_version()
        health_status["checks"]["tesseract"] = f"healthy (v{version})"
    except Exception as e:
        logger.warning(f"Health check tesseract failed: {e}")
        health_status["checks"]["tesseract"] = "unhealthy"
        health_status["status"] = "degraded"

    # Check Azure Blob Storage (if configured)
    if settings.azure_storage_connection_string:
        health_status["checks"]["blob_storage"] = "configured"
    else:
        health_status["checks"]["blob_storage"] = "not configured"

    # Check Stripe (if configured)
    if settings.stripe_secret_key:
        health_status["checks"]["stripe"] = "configured"
    else:
        health_status["checks"]["stripe"] = "not configured"

    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)

    return health_status


@router.get("/ready")
async def readiness_check():
    """
    Readiness probe for Kubernetes/Azure Container Apps.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))

        pytesseract.get_tesseract_version()

        return {"status": "ready"}

    except Exception as e:
        logger.warning(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={"status": "not ready"}
        )


@router.get("/live")
async def liveness_check():
    """
    Liveness probe for Kubernetes/Azure Container Apps.
    """
    return {"status": "alive"}
