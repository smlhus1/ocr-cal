"""
Download/generate calendar endpoint.
"""
import logging
import os
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.models import GenerateCalendarRequest
from app.ocr.processor import VaktplanProcessor
from app.config import settings

logger = logging.getLogger('shiftsync')

router = APIRouter()


def sanitize_filename(name: str) -> str:
    """Sanitize a string for safe use in HTTP headers and filenames."""
    return re.sub(r'[^\w\-.]', '_', name)[:50]


@router.post("/generate-calendar")
async def generate_calendar(request: GenerateCalendarRequest):
    """
    Generate iCalendar (.ics) file from shifts.
    """
    try:
        if not request.shifts:
            raise HTTPException(
                status_code=400,
                detail="No shifts provided"
            )

        if len(request.shifts) > 100:
            raise HTTPException(
                status_code=400,
                detail="Too many shifts (max 100)"
            )

        # Initialize processor (only for calendar generation)
        processor = VaktplanProcessor(
            tesseract_path=settings.tesseract_path,
            language=settings.ocr_language
        )

        # Generate iCalendar file
        ics_bytes = processor.generate_ics(
            shifts=request.shifts,
            owner_name=request.owner_name
        )

        # Sanitize owner_name for Content-Disposition header
        safe_name = sanitize_filename(request.owner_name) if request.owner_name else "vakter"

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
        logger.error(f"Calendar generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Calendar generation failed. Please try again."
        )


@router.get("/download/{upload_id}")
async def download_original(upload_id: str):
    """
    Download original uploaded file.
    Available for 24h after upload.

    NOTE: This endpoint has no authentication. Consider adding a download token
    if IDOR is a concern in production.
    """
    from app.storage.blob_storage import get_storage_service

    storage = get_storage_service()
    file_path = await storage.download_file(upload_id)

    if not file_path:
        raise HTTPException(
            status_code=404,
            detail="File not found or expired (files are deleted after 24h)"
        )

    ext = os.path.splitext(file_path)[1].lower()
    content_type_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.pdf': 'application/pdf'
    }
    content_type = content_type_map.get(ext, 'application/octet-stream')

    with open(file_path, 'rb') as f:
        content = f.read()

    # Cleanup temp file
    try:
        os.unlink(file_path)
    except Exception as e:
        logger.warning(f"Could not clean up temp file: {e}")

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="vaktplan{ext}"'
        }
    )
