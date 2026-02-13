"""
Database connection and models using SQLAlchemy with async support.
Only stores anonymized metadata - NO personal data.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, CHAR, Uuid
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import settings


# Create async engine with connection pool settings
_db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
_engine_kwargs = {
    "echo": settings.environment == "development",
    "future": True,
}
# Pool settings only apply to connection-pooling backends (not SQLite)
if not _db_url.startswith("sqlite"):
    _engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,
    })
engine = create_async_engine(_db_url, **_engine_kwargs)

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
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Session tracking (anonymous cookie, not PII)
    session_id = Column(String(36), index=True)

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


class AnonymousSession(Base):
    """
    Tracks anonymous browser sessions for quota enforcement.
    No PII - just a random UUID cookie mapped to subscription status.
    """
    __tablename__ = "anonymous_sessions"

    session_id = Column(String(36), primary_key=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default='free')  # 'free', 'premium', 'cancelled'
    credits = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class FeedbackLog(Base):
    """
    Stores anonymized user feedback for ML improvements.
    No personal data - only correction patterns.
    """
    __tablename__ = "feedback_log"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Reference to original upload (for correlation)
    upload_id = Column(Uuid, nullable=False)
    
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
    country_code: Optional[str] = None,
    session_id: Optional[str] = None
):
    """
    Log upload metadata.
    Returns upload UUID.
    """
    async with AsyncSessionLocal() as session:
        upload = UploadAnalytics(
            file_format=file_format,
            file_size_kb=file_size_kb,
            country_code=country_code,
            session_id=session_id,
            success=False,  # Will be updated after processing
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )

        session.add(upload)
        await session.commit()
        await session.refresh(upload)

        return upload.id


async def get_upload_count_this_month(session_id: str) -> int:
    """Count uploads this month for a given session."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, func

        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        stmt = select(func.count(UploadAnalytics.id)).where(
            UploadAnalytics.session_id == session_id,
            UploadAnalytics.created_at >= month_start
        )

        result = await session.execute(stmt)
        return result.scalar() or 0


async def get_session(session_id: str) -> Optional[AnonymousSession]:
    """Get anonymous session by ID."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        stmt = select(AnonymousSession).where(
            AnonymousSession.session_id == session_id
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def upsert_session(
    session_id: str,
    stripe_subscription_id: Optional[str] = None,
    status: str = 'free'
) -> None:
    """Create or update anonymous session."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        existing = await session.execute(
            select(AnonymousSession).where(AnonymousSession.session_id == session_id)
        )
        row = existing.scalar_one_or_none()

        if row:
            row.stripe_subscription_id = stripe_subscription_id
            row.status = status
            row.updated_at = datetime.now(timezone.utc)
        else:
            session.add(AnonymousSession(
                session_id=session_id,
                stripe_subscription_id=stripe_subscription_id,
                status=status,
            ))

        await session.commit()


async def get_credit_balance(session_id: str) -> int:
    """Get credit balance for a session."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        stmt = select(AnonymousSession.credits).where(
            AnonymousSession.session_id == session_id
        )
        result = await session.execute(stmt)
        balance = result.scalar_one_or_none()
        return balance if balance is not None else 0


async def add_credits(session_id: str, amount: int) -> None:
    """Add credits to a session (upserts if session doesn't exist)."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        existing = await session.execute(
            select(AnonymousSession).where(AnonymousSession.session_id == session_id)
        )
        row = existing.scalar_one_or_none()

        if row:
            row.credits = row.credits + amount
            row.updated_at = datetime.now(timezone.utc)
        else:
            session.add(AnonymousSession(
                session_id=session_id,
                credits=amount,
            ))

        await session.commit()


async def deduct_credit(session_id: str) -> bool:
    """Deduct 1 credit from session. Returns True if successful, False if insufficient."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        existing = await session.execute(
            select(AnonymousSession).where(AnonymousSession.session_id == session_id)
        )
        row = existing.scalar_one_or_none()

        if not row or row.credits <= 0:
            return False

        row.credits = row.credits - 1
        row.updated_at = datetime.now(timezone.utc)
        await session.commit()
        return True


async def log_processing_result(
    upload_id,
    shifts_found: int,
    confidence_score: float,
    processing_time_ms: int,
    success: bool,
    error_type: Optional[str] = None,
    ocr_engine: str = "tesseract"
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
            ocr_engine=ocr_engine
        )

        await session.execute(stmt)
        await session.commit()

