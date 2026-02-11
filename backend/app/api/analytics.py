"""
Internal analytics endpoint (requires API key).
For monitoring and insights into OCR performance.
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import APIKeyHeader
from typing import Optional

from app.config import settings
from app.database import (
    get_success_rate,
    get_format_distribution,
    get_average_confidence
)


router = APIRouter()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Depends(api_key_header)):
    """
    Verify API key for internal endpoints.
    Uses dedicated INTERNAL_API_KEY from environment.
    """
    # Use dedicated internal API key
    expected_key = settings.internal_api_key
    
    # If no internal API key is configured, block all access
    if not expected_key:
        raise HTTPException(
            status_code=503,
            detail="Internal API not configured. Set INTERNAL_API_KEY in environment."
        )
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Include X-API-Key header."
        )
    
    # Constant-time comparison to prevent timing attacks
    import secrets
    if not secrets.compare_digest(api_key, expected_key):
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return True


@router.get("/analytics")
async def get_analytics(
    days: int = 7,
    authorized: bool = Depends(verify_api_key)
):
    """
    Get aggregated analytics data.
    
    Requires API key authentication.
    
    Args:
        days: Number of days to analyze (default: 7)
        
    Returns:
        Analytics summary with success rate, format distribution, etc.
    """
    try:
        # Get analytics data
        success_rate = await get_success_rate(days=days)
        format_dist = await get_format_distribution(days=days)
        avg_confidence = await get_average_confidence(days=days)
        
        return {
            "period_days": days,
            "success_rate": round(success_rate * 100, 2),  # As percentage
            "average_confidence": round(avg_confidence, 3),
            "format_distribution": {
                fmt: round(pct * 100, 2) for fmt, pct in format_dist.items()
            },
            "metrics": {
                "total_uploads": sum(format_dist.values()) if format_dist else 0,
                "status": "healthy" if success_rate > 0.7 else "needs_attention"
            }
        }
        
    except Exception as e:
        import logging
        logging.getLogger('shiftsync').error(f"Analytics query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Analytics query failed"
        )


@router.get("/health-detailed")
async def health_check_detailed(authorized: bool = Depends(verify_api_key)):
    """
    Detailed health check with system status.
    
    Requires API key authentication.
    
    Returns:
        System health metrics
    """
    import psutil
    import sys
    
    try:
        return {
            "status": "healthy",
            "environment": settings.environment,
            "python_version": sys.version.split()[0],
            "tesseract_configured": settings.tesseract_path is not None,
            "database_configured": settings.database_url is not None,
            "storage_configured": settings.azure_storage_connection_string is not None,
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            }
        }
    except Exception as e:
        import logging
        logging.getLogger('shiftsync').error(f"Health check failed: {e}")
        return {
            "status": "degraded",
            "error": "System check failed"
        }

