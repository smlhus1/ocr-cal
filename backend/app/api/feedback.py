"""
Feedback endpoint for user-reported corrections.
Enables smart learning from anonymized data.
"""
import logging

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import insert

from app.models import FeedbackRequest
from app.database import AsyncSessionLocal, FeedbackLog
from app.security import limiter

logger = logging.getLogger('shiftsync')

router = APIRouter()


@router.post("/feedback")
@limiter.limit("5/minute")
async def report_feedback(request: Request, feedback: FeedbackRequest):
    """
    Report feedback on OCR results.
    
    Users can report errors after reviewing OCR results.
    This data is stored anonymously to improve OCR accuracy over time.
    
    Args:
        request: Feedback with error type and correction data
        
    Returns:
        Confirmation message
        
    Raises:
        400: Invalid feedback data
    """
    try:
        # Anonymize correction data (remove any potential personal info)
        correction_pattern = None
        if feedback.correction_data:
            # Extract pattern without personal data
            # Example: {"wrong_format": "DD/MM/YYYY", "expected": "DD.MM.YYYY"}
            correction_pattern = _anonymize_correction(feedback.correction_data)

        # Store in database
        async with AsyncSessionLocal() as session:
            feedback_log = FeedbackLog(
                upload_id=feedback.upload_id,
                error_type=feedback.error_type,
                correction_pattern=correction_pattern
            )
            session.add(feedback_log)
            await session.commit()
        
        return {
            "status": "feedback_recorded",
            "message": "Takk for tilbakemeldingen! Dette hjelper oss å forbedre OCR-nøyaktigheten."
        }
        
    except Exception as e:
        logger.error("Could not record feedback: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Could not record feedback. Please try again later."
        )


def _anonymize_correction(correction_data: dict) -> str:
    """
    Anonymize correction data by removing personal information.
    
    Args:
        correction_data: Raw correction data from user
        
    Returns:
        Anonymized pattern string (max 500 chars)
    """
    import re
    
    # Convert to string
    correction_str = str(correction_data)
    
    # Remove potential names (capitalize words)
    correction_str = re.sub(r'\b[A-ZÆØÅ][a-zæøå]+\b', '[NAME]', correction_str)
    
    # Remove potential phone numbers
    correction_str = re.sub(r'\d{8,}', '[PHONE]', correction_str)
    
    # Remove potential emails
    correction_str = re.sub(r'\S+@\S+\.\S+', '[EMAIL]', correction_str)
    
    # Truncate if too long
    if len(correction_str) > 500:
        correction_str = correction_str[:497] + "..."
    
    return correction_str

