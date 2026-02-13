"""
Upload endpoint for shift schedule files.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, UploadFile, File, Request, HTTPException
from fastapi.responses import JSONResponse

from app.models import UploadResponse, QuotaExceededResponse
from app.security import limiter, validate_file, get_user_identifier, get_country_code, scan_file_for_malware
from app.storage.blob_storage import get_storage_service
from app.database import log_upload, deduct_credit

logger = logging.getLogger('shiftsync')


router = APIRouter()
storage = get_storage_service()


@router.post("/upload", response_model=UploadResponse)
@limiter.limit("10/minute")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """
    Upload shift schedule file for processing.
    
    Security:
    - Rate limited: 10 uploads per minute per IP
    - File validation: Type, size, signature
    - Quota enforcement: Free tier gets 2/month
    
    Args:
        file: Uploaded file (image/jpeg, image/png, application/pdf)
        
    Returns:
        Upload ID and expiration time
        
    Raises:
        413: File too large
        400: Invalid file type
        402: Quota exceeded
        429: Rate limit exceeded
    """
    # Check quota (free tier + credits enforcement via session cookie)
    from app.payment import payment_service

    session_id = getattr(request.state, 'session_id', None)
    if not session_id:
        session_id = request.cookies.get('session_id', 'unknown')
    has_quota, free_remaining, credits = await payment_service.check_quota(session_id)
    use_paid_credits = (free_remaining == 0 and credits > 0)

    if not has_quota:
        # Build credit packs for 402 response
        credit_packs = [
            {
                "pack_id": pack_id,
                "credits": pack["credits"],
                "price_nok": pack["price_nok"] / 100,
                "name": pack["name"],
            }
            for pack_id, pack in payment_service.CREDIT_PACKS.items()
        ]

        return JSONResponse(
            status_code=402,
            content={
                "error": "quota_exceeded",
                "message": f"Du har brukt opp gratis-kvoten ({payment_service.FREE_TIER_LIMIT} per måned). Kjøp kreditter for å fortsette.",
                "credit_packs": credit_packs,
            }
        )
    
    # Validate file (returns content to avoid double-read)
    try:
        file_content = await validate_file(file)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.warning("File validation failed: %s", e)
        raise HTTPException(status_code=400, detail="File validation failed")

    # Generate upload ID
    upload_id = str(uuid.uuid4())
    
    # Upload to storage
    try:
        blob_url = await storage.upload_file(
            upload_id=upload_id,
            file_content=file_content,
            content_type=file.content_type or "application/octet-stream"
        )
    except Exception as e:
        logger.error("Storage upload failed: %s", e)
        raise HTTPException(status_code=500, detail="Storage upload failed")
    
    # Scan for malware (after upload, before processing)
    try:
        file_path = await storage.get_file_path(upload_id)
        is_safe = await scan_file_for_malware(file_path)
        if not is_safe:
            # Delete the malicious file
            await storage.delete_file(upload_id)
            raise HTTPException(
                status_code=400,
                detail="File rejected: Potential security threat detected"
            )
    except HTTPException:
        raise
    except Exception as e:
        # Log but don't fail - malware scanning is best-effort in development
        logger.warning("Malware scan skipped: %s", e)
    
    # Log to database (anonymized)
    file_size_kb = len(file_content) // 1024
    file_format = file.content_type.split('/')[-1] if file.content_type else 'unknown'
    country = get_country_code(request)
    
    try:
        await log_upload(
            file_format=file_format,
            file_size_kb=file_size_kb,
            country_code=country,
            session_id=session_id
        )
    except Exception as e:
        logger.warning("Could not log upload to database: %s", e)
    
    # Deduct credit if using paid credits
    if use_paid_credits:
        deducted = await deduct_credit(session_id)
        if not deducted:
            logger.warning("Credit deduction failed for session %s", session_id[:8])

    # Return response
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    return UploadResponse(
        upload_id=upload_id,
        status="uploaded",
        expires_at=expires_at
    )

