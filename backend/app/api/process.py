"""
Process endpoint for OCR processing of uploaded files.
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
import asyncio
import logging
import time
import os

from app.models import ProcessRequest, ProcessResponse, Shift
from app.storage.blob_storage import get_storage_service
from app.ocr.processor import VaktplanProcessor
from app.ocr.vision_processor import VisionProcessor
from app.ocr.confidence_scorer import assign_individual_confidences, generate_warnings
from app.database import log_processing_result
from app.config import settings
from app.security import limiter

logger = logging.getLogger('shiftsync')

router = APIRouter()
storage = get_storage_service()


@router.post("/process", response_model=ProcessResponse)
@limiter.limit("5/minute")
async def process_upload(request: Request, body: ProcessRequest):
    """
    Process uploaded file with OCR or AI Vision.

    Rate limited to 5 requests per minute per client.
    """
    start_time = time.time()

    # Download file from storage
    file_path = await storage.download_file(body.upload_id)

    if not file_path:
        raise HTTPException(
            status_code=404,
            detail="Upload not found or expired"
        )

    try:
        logger.info(f"Processing method: {body.method.upper()}")

        if body.method == "ai":
            if not settings.openai_api_key:
                raise HTTPException(
                    status_code=400,
                    detail="AI processing requires OpenAI API key to be configured."
                )

            logger.info("Using GPT-4 Vision processor")

            try:
                processor = VisionProcessor(api_key=settings.openai_api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Vision processor: {e}")
                raise

            # Vision processor uses httpx (async-compatible), run in thread for safety
            shifts, overall_confidence = await asyncio.to_thread(
                processor.process_image,
                file_path,
                settings.environment == "development"
            )
            logger.info(f"Vision completed: {len(shifts)} shifts, {overall_confidence:.2%} confidence")
        else:
            logger.info("Using Tesseract OCR")
            processor = VaktplanProcessor(
                tesseract_path=settings.tesseract_path,
                language=settings.ocr_language
            )

            # Tesseract is synchronous - run in thread to not block event loop
            shifts, overall_confidence = await asyncio.to_thread(
                processor.process_image,
                file_path,
                settings.environment == "development"
            )
            logger.info(f"OCR completed: {len(shifts)} shifts, {overall_confidence:.2%} confidence")

        # Convert dataclass shifts to Pydantic models
        pydantic_shifts = []
        for shift in shifts:
            pydantic_shifts.append(Shift(
                date=shift.date,
                start_time=shift.start_time,
                end_time=shift.end_time,
                shift_type=shift.shift_type,
                confidence=shift.confidence
            ))

        # Assign individual confidence scores using OCR text from processor
        # For OCR method, re-read text in thread; for AI, use shifts as-is
        if pydantic_shifts and body.method != "ai":
            from PIL import Image
            import pytesseract

            def _read_ocr_text():
                image = Image.open(file_path)
                return pytesseract.image_to_string(image, lang=settings.ocr_language, timeout=30)

            ocr_text = await asyncio.to_thread(_read_ocr_text)
            pydantic_shifts = assign_individual_confidences(pydantic_shifts, ocr_text)

        # Generate warnings
        warnings = generate_warnings(pydantic_shifts, overall_confidence)

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Log results to database
        try:
            await log_processing_result(
                upload_id=body.upload_id,
                shifts_found=len(pydantic_shifts),
                confidence_score=overall_confidence,
                processing_time_ms=processing_time_ms,
                success=len(pydantic_shifts) > 0,
                error_type=None if len(pydantic_shifts) > 0 else "no_shifts_found"
            )
        except Exception as e:
            logger.warning(f"Could not log processing result: {e}")

        return ProcessResponse(
            shifts=pydantic_shifts,
            confidence=overall_confidence,
            warnings=warnings,
            processing_time_ms=processing_time_ms
        )

    except HTTPException:
        raise
    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Processing failed for upload {body.upload_id}: {e}")

        try:
            await log_processing_result(
                upload_id=body.upload_id,
                shifts_found=0,
                confidence_score=0.0,
                processing_time_ms=processing_time_ms,
                success=False,
                error_type="processing_error"
            )
        except Exception as log_err:
            logger.warning(f"Could not log error result: {log_err}")

        raise HTTPException(
            status_code=500,
            detail="OCR processing failed. Please try again."
        )

    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except Exception as e:
                logger.warning(f"Could not clean up temp file: {e}")

