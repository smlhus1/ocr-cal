"""
Process endpoint for OCR processing of uploaded files.
"""
import asyncio
import json
import logging
import os
import time

from fastapi import APIRouter, HTTPException, Request
from openai import RateLimitError, APITimeoutError

from app.models import ProcessRequest, ProcessResponse
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

    ocr_engine = body.method  # "ocr" or "ai"
    vision_proc = None

    try:
        logger.info("Processing method: %s", body.method.upper())

        warnings = []

        if body.method == "ai":
            if not settings.openai_api_key:
                raise HTTPException(
                    status_code=400,
                    detail="AI processing requires OpenAI API key to be configured."
                )

            logger.info("Using GPT-4 Vision processor")

            try:
                vision_proc = VisionProcessor(api_key=settings.openai_api_key)

                # Vision processor returns (shifts, confidence) - no ocr_text
                shifts, overall_confidence = await asyncio.to_thread(
                    vision_proc.process_image,
                    file_path,
                    settings.environment == "development"
                )
                ocr_engine = "gpt4-vision"
                logger.info("Vision completed: %d shifts, %.2f%% confidence", len(shifts), overall_confidence * 100)

            except Exception as vision_error:
                # Fallback to Tesseract if Vision fails
                logger.warning("Vision failed, falling back to Tesseract: %s", vision_error)

                try:
                    processor = VaktplanProcessor(
                        tesseract_path=settings.tesseract_path,
                        language=settings.ocr_language
                    )
                    shifts, overall_confidence, ocr_text = await asyncio.to_thread(
                        processor.process_image, file_path,
                        settings.environment == "development"
                    )
                    ocr_engine = "tesseract-fallback"

                    if shifts:
                        shifts = assign_individual_confidences(shifts, ocr_text)

                    warnings.append(
                        "AI-prosessering feilet. Resultater er fra Tesseract OCR (kan ha lavere nøyaktighet)."
                    )
                    logger.info("Fallback OCR completed: %d shifts", len(shifts))
                except Exception:
                    # Both engines failed - re-raise the original Vision error
                    raise vision_error

        else:
            logger.info("Using Tesseract OCR")
            processor = VaktplanProcessor(
                tesseract_path=settings.tesseract_path,
                language=settings.ocr_language
            )

            # Tesseract is synchronous - run in thread to not block event loop
            # process_image now returns (shifts, confidence, ocr_text)
            shifts, overall_confidence, ocr_text = await asyncio.to_thread(
                processor.process_image,
                file_path,
                settings.environment == "development"
            )
            ocr_engine = "tesseract"
            logger.info("OCR completed: %d shifts, %.2f%% confidence", len(shifts), overall_confidence * 100)

            # Assign individual confidence scores using already-extracted OCR text
            if shifts:
                shifts = assign_individual_confidences(shifts, ocr_text)

        # Generate warnings (append to any existing fallback warnings)
        warnings.extend(generate_warnings(shifts, overall_confidence))

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Log results to database
        try:
            await log_processing_result(
                upload_id=body.upload_id,
                shifts_found=len(shifts),
                confidence_score=overall_confidence,
                processing_time_ms=processing_time_ms,
                success=len(shifts) > 0,
                error_type=None if len(shifts) > 0 else "no_shifts_found",
                ocr_engine=ocr_engine
            )
        except Exception as e:
            logger.warning("Could not log processing result: %s", e)

        return ProcessResponse(
            shifts=shifts,
            confidence=overall_confidence,
            warnings=warnings,
            processing_time_ms=processing_time_ms
        )

    except HTTPException:
        raise
    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.error("Processing failed for upload %s: %s", body.upload_id, e)

        # Granular error classification for analytics
        if isinstance(e, RateLimitError):
            error_type = "vision_rate_limit"
        elif isinstance(e, APITimeoutError):
            error_type = "vision_timeout"
        elif isinstance(e, json.JSONDecodeError):
            error_type = "vision_json_error"
        elif isinstance(e, FileNotFoundError):
            error_type = "file_not_found"
        else:
            error_type = "processing_error"

        try:
            await log_processing_result(
                upload_id=body.upload_id,
                shifts_found=0,
                confidence_score=0.0,
                processing_time_ms=processing_time_ms,
                success=False,
                error_type=error_type,
                ocr_engine=ocr_engine
            )
        except Exception as log_err:
            logger.warning("Could not log error result: %s", log_err)

        raise HTTPException(
            status_code=500,
            detail="OCR processing failed. Please try again."
        )

    finally:
        # Clean up vision processor httpx client
        if vision_proc is not None:
            vision_proc.close()

        if file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except Exception as e:
                logger.warning("Could not clean up temp file: %s", e)
