"""
Download/generate calendar endpoint.
"""
import logging
import os
import re

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

from app.models import GenerateCalendarRequest
from app.ocr.calendar_generator import generate_ics
from app.security import limiter, generate_download_token, validate_download_token

logger = logging.getLogger('shiftsync')

router = APIRouter()


def sanitize_filename(name: str) -> str:
    """Sanitize a string for safe use in HTTP headers and filenames."""
    return re.sub(r'[^\w\-.]', '_', name)[:50]


@router.post("/generate-calendar")
@limiter.limit("20/minute")
async def generate_calendar(request: Request, calendar_request: GenerateCalendarRequest):
    """
    Generate iCalendar (.ics) file from shifts.
    """
    try:
        if not calendar_request.shifts:
            raise HTTPException(
                status_code=400,
                detail="No shifts provided"
            )

        if len(calendar_request.shifts) > 100:
            raise HTTPException(
                status_code=400,
                detail="Too many shifts (max 100)"
            )

        # Generate iCalendar file
        ics_bytes = generate_ics(
            shifts=calendar_request.shifts,
            owner_name=calendar_request.owner_name
        )

        # Sanitize owner_name for Content-Disposition header
        safe_name = sanitize_filename(calendar_request.owner_name) if calendar_request.owner_name else "vakter"

        return Response(
            content=ics_bytes,
            media_type="text/calendar",
            headers={
                "Content-Disposition": f'attachment; filename="vakter_{safe_name}.ics"',
                "Content-Type": "text/calendar; charset=utf-8"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Calendar generation failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Calendar generation failed. Please try again."
        )


@router.post("/download-token/{upload_id}")
@limiter.limit("10/minute")
async def get_download_token(request: Request, upload_id: str):
    """
    Generate a short-lived download token for a specific upload.
    Token is HMAC-signed and expires after 10 minutes.
    """
    token = generate_download_token(upload_id)
    return {"token": token}


@router.get("/download/{upload_id}")
@limiter.limit("10/minute")
async def download_original(
    request: Request,
    upload_id: str,
    token: str = Query(..., description="HMAC-signed download token")
):
    """
    Download original uploaded file.
    Available for 24h after upload.
    Requires a valid download token obtained from POST /download-token/{upload_id}.
    """
    # Verify download token
    validate_download_token(upload_id, token)

    from app.storage.blob_storage import get_storage_service

    storage = get_storage_service()
    file_path = await storage.download_file(upload_id)

    if not file_path:
        raise HTTPException(
            status_code=404,
            detail="File not found or expired (files are deleted after 24h)"
        )

    from app.models import EXTENSION_TO_MIME

    ext = os.path.splitext(file_path)[1].lower()
    content_type = EXTENSION_TO_MIME.get(ext, 'application/octet-stream')

    with open(file_path, 'rb') as f:
        content = f.read()

    # Cleanup temp file
    try:
        os.unlink(file_path)
    except Exception as e:
        logger.warning("Could not clean up temp file: %s", e)

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="vaktplan{ext}"'
        }
    )
