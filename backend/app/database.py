"""
Database connection and models using SQLAlchemy with async support.
Only stores anonymized metadata - NO personal data.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, CHAR
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import settings


# Create async engine with connection pool settings
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.environment == "development",
    future=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()


class UploadAnalytics(Base):
    """
    Stores anonymized analytics for uploads.
    GDPR-compliant: No personal data, auto-delete after 24h.
    """
    __tablename__ = "upload_analytics"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    # File metadata (anonymized)
    file_format = Column(String(10), nullable=False, index=True)  # 'jpeg', 'png', 'pdf'
    file_size_kb = Column(Integer)
    
    # OCR results (anonymized)
    ocr_engine = Column(String(20))  # 'tesseract', 'azure', etc.
    shifts_found = Column(Integer)
    confidence_score = Column(Float)
    processing_time_ms = Column(Integer)
    success = Column(Boolean, nullable=False)
    
    # Error tracking (no personal data)
    error_type = Column(String(50))
    
    # Geography (country-level only, for stats)
    country_code = Column(CHAR(2))  # ISO 3166-1 alpha-2
    
    # Blob storage reference (for cleanup)
    blob_id = Column(String(100))
    expires_at = Column(DateTime, nullable=False, index=True)
    
    def __repr__(self):
        return f"<UploadAnalytics(id={self.id}, format={self.file_format}, success={self.success})>"


class FeedbackLog(Base):
    """
    Stores anonymized user feedback for ML improvements.
    No personal data - only correction patterns.
    """
    __tablename__ = "feedback_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Reference to original upload (for correlation)
    upload_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Error type
    error_type = Column(String(50), nullable=False)  # 'wrong_date', 'missing_shift', etc.
    
    # Anonymized correction data (JSON)
    # Example: {"expected_format": "DD.MM.YYYY", "detected_format": "MM/DD/YYYY"}
    correction_pattern = Column(String(500))
    
    def __repr__(self):
        return f"<FeedbackLog(id={self.id}, error_type={self.error_type})>"


# Database helper functions

async def get_db() -> AsyncSession:
    """
    Dependency for getting database session.
    Use with FastAPI Depends().
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def cleanup_expired_records():
    """
    Clean up expired records (24h+ old).
    Should be run as scheduled job.
    """
    async with AsyncSessionLocal() as session:
        from sqlalchemy import delete
        
        # Delete expired upload analytics
        stmt = delete(UploadAnalytics).where(
            UploadAnalytics.expires_at < datetime.now(timezone.utc)
        )
        result = await session.execute(stmt)
        await session.commit()
        
        return result.rowcount


# Analytics queries

async def get_success_rate(days: int = 7) -> float:
    """Get success rate for last N days."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, func
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        stmt = select(
            func.count(UploadAnalytics.id).label('total'),
            func.sum(func.cast(UploadAnalytics.success, Integer)).label('successful')
        ).where(UploadAnalytics.created_at >= cutoff_date)
        
        result = await session.execute(stmt)
        row = result.one()
        
        if row.total == 0:
            return 0.0
        
        return (row.successful or 0) / row.total


async def get_format_distribution(days: int = 30) -> dict:
    """Get file format distribution for last N days."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, func
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        stmt = select(
            UploadAnalytics.file_format,
            func.count(UploadAnalytics.id).label('count')
        ).where(
            UploadAnalytics.created_at >= cutoff_date
        ).group_by(UploadAnalytics.file_format)
        
        result = await session.execute(stmt)
        rows = result.all()
        
        total = sum(row.count for row in rows)
        if total == 0:
            return {}
        
        return {row.file_format: row.count / total for row in rows}


async def get_average_confidence(days: int = 7) -> float:
    """Get average confidence score for last N days."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, func
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        stmt = select(
            func.avg(UploadAnalytics.confidence_score)
        ).where(
            UploadAnalytics.created_at >= cutoff_date,
            UploadAnalytics.success == True
        )
        
        result = await session.execute(stmt)
        avg = result.scalar()
        
        return float(avg) if avg else 0.0


async def log_upload(
    file_format: str,
    file_size_kb: int,
    country_code: Optional[str] = None
) -> UUID:
    """
    Log upload metadata.
    Returns upload UUID.
    """
    async with AsyncSessionLocal() as session:
        upload = UploadAnalytics(
            file_format=file_format,
            file_size_kb=file_size_kb,
            country_code=country_code,
            success=False,  # Will be updated after processing
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        
        session.add(upload)
        await session.commit()
        await session.refresh(upload)
        
        return upload.id


async def log_processing_result(
    upload_id: UUID,
    shifts_found: int,
    confidence_score: float,
    processing_time_ms: int,
    success: bool,
    error_type: Optional[str] = None
):
    """Update upload record with processing results."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, update
        
        stmt = update(UploadAnalytics).where(
            UploadAnalytics.id == upload_id
        ).values(
            shifts_found=shifts_found,
            confidence_score=confidence_score,
            processing_time_ms=processing_time_ms,
            success=success,
            error_type=error_type,
            ocr_engine='tesseract'
        )
        
        await session.execute(stmt)
        await session.commit()

