"""
Pydantic models for request/response validation and data structures.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Literal, List, Optional
from datetime import datetime


class UploadRequest(BaseModel):
    """Validation for file upload metadata."""
    file_size: int = Field(..., gt=0, le=10_000_000, description="File size in bytes (max 10MB)")
    file_type: Literal["image/jpeg", "image/png", "application/pdf"]


class UploadResponse(BaseModel):
    """Response after successful upload."""
    upload_id: str
    status: Literal["uploaded"]
    expires_at: datetime


class ProcessRequest(BaseModel):
    """Request to process an uploaded file."""
    upload_id: str = Field(..., pattern=r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')
    method: Literal["ocr", "ai"] = Field(default="ocr", description="Processing method: 'ocr' (Tesseract) or 'ai' (GPT-4 Vision)")
    
    @field_validator('upload_id')
    @classmethod
    def validate_uuid(cls, v):
        """Ensure upload_id is a valid UUID format."""
        if not v:
            raise ValueError('upload_id cannot be empty')
        return v.lower()


class Shift(BaseModel):
    """Represents a single work shift."""
    date: str = Field(..., pattern=r'^\d{2}\.\d{2}\.\d{4}$', description="Format: DD.MM.YYYY")
    start_time: str = Field(..., pattern=r'^\d{2}:\d{2}$', description="Format: HH:MM")
    end_time: str = Field(..., pattern=r'^\d{2}:\d{2}$', description="Format: HH:MM")
    shift_type: Literal["tidlig", "mellom", "kveld", "natt"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        """Validate date format and values."""
        parts = v.split('.')
        if len(parts) != 3:
            raise ValueError('Date must be in DD.MM.YYYY format')
        day, month, year = map(int, parts)
        if not (1 <= day <= 31 and 1 <= month <= 12 and 2020 <= year <= 2030):
            raise ValueError('Invalid date values')
        return v


class ProcessResponse(BaseModel):
    """Response after OCR processing."""
    shifts: List[Shift]
    confidence: float = Field(..., ge=0.0, le=1.0)
    warnings: List[str] = []
    processing_time_ms: int


class GenerateCalendarRequest(BaseModel):
    """Request to generate calendar file."""
    shifts: List[Shift] = Field(..., min_length=1, max_length=100)
    owner_name: str = Field(..., min_length=1, max_length=100)
    
    @field_validator('owner_name')
    @classmethod
    def validate_owner_name(cls, v):
        """Sanitize owner name."""
        # Remove any potential XSS/injection attempts
        return v.strip()


class FeedbackRequest(BaseModel):
    """User feedback on OCR results."""
    upload_id: str = Field(..., pattern=r'^[a-fA-F0-9-]{36}$')
    error_type: Literal["wrong_date", "missing_shift", "wrong_time", "wrong_type", "other"]
    correction_data: Optional[dict] = None


class QuotaExceededResponse(BaseModel):
    """Response when quota is exceeded."""
    error: Literal["quota_exceeded"]
    message: str
    upgrade_url: str

