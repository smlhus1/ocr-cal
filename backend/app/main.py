"""
FastAPI main application with security middleware and routing.
"""
import re
import time
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.security import limiter
from app.logging_config import setup_logging, setup_sentry, logger

# Initialize logging and error tracking
setup_logging(log_level="DEBUG" if settings.environment == "development" else "INFO")
setup_sentry()


# Create FastAPI app
app = FastAPI(
    title="ShiftSync API",
    description="OCR-based shift schedule converter with smart learning",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,  # Hide docs in production
    redoc_url="/redoc" if settings.environment != "production" else None
)

# Add rate limiter with response headers
from slowapi.middleware import SlowAPIMiddleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# HTTPS redirect in production
if settings.environment == "production":
    app.add_middleware(HTTPSRedirectMiddleware)


# CORS middleware
allowed_origins = [settings.frontend_url]
if settings.environment == "production":
    allowed_origins = ["https://shiftsync.no", "https://www.shiftsync.no"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,  # Required for session cookies
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    max_age=3600,
)


# IP-based rate limiter for new session creation (H-02: session rotation bypass)
_session_creation_times: dict[str, list[float]] = defaultdict(list)
_SESSION_RATE_LIMIT = 10  # max new sessions per IP per minute
_SESSION_RATE_WINDOW = 60  # seconds


# Session cookie middleware
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    """Set anonymous session cookie for quota tracking."""
    import uuid as _uuid
    from slowapi.util import get_remote_address

    session_id = request.cookies.get("session_id")
    is_new_session = not session_id

    if is_new_session:
        # Rate limit new session creation per IP
        ip = get_remote_address(request)
        now = time.time()
        # Clean old entries
        _session_creation_times[ip] = [
            t for t in _session_creation_times[ip] if now - t < _SESSION_RATE_WINDOW
        ]
        if len(_session_creation_times[ip]) >= _SESSION_RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many new sessions. Please try again later."},
            )
        _session_creation_times[ip].append(now)
        session_id = str(_uuid.uuid4())

    request.state.session_id = session_id

    response = await call_next(request)

    # Set cookie if not present (30 days, HttpOnly, SameSite=Lax)
    if is_new_session:
        response.set_cookie(
            key="session_id",
            value=session_id,
            max_age=30 * 24 * 3600,  # 30 days
            httponly=True,
            samesite="lax",
            secure=settings.environment == "production",
        )

    return response


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; "
        "frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
    )
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), usb=()"

    return response


# UUID regex for validating X-Request-ID
_UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Generate or forward X-Request-ID for request tracing."""
    import uuid
    incoming_id = request.headers.get("X-Request-ID")
    # Only accept valid UUIDs to prevent header injection
    if incoming_id and _UUID_RE.match(incoming_id):
        request_id = incoming_id
    else:
        request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Request timing and audit logging middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Track request processing time and log for audit."""
    start_time = time.time()

    # Get client identifier (hashed IP for privacy)
    from app.security import get_user_identifier
    try:
        client_id = get_user_identifier(request)[:8]
    except Exception:
        client_id = "unknown"

    request_id = getattr(request.state, "request_id", "unknown")

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000  # Convert to ms
    response.headers["X-Process-Time-Ms"] = str(int(process_time))

    # Audit log (sanitized - no personal data)
    logger.info(
        "AUDIT | %s %s | client=%s | request_id=%s | status=%s | time=%dms",
        request.method, request.url.path, client_id, request_id,
        response.status_code, int(process_time)
    )

    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return a safe error response."""
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again later."}
    )


# Root endpoint
@app.get("/")
async def root():
    """API root with basic info."""
    return {
        "service": "ShiftSync API",
        "version": "1.0.0",
        "documentation": "/docs" if settings.environment != "production" else None
    }


# Import and include routers
from app.api import upload, process, download, analytics, feedback, payment
from app import health
from app.cleanup import start_cleanup_scheduler


# Startup event - initialize background tasks
@app.on_event("startup")
async def startup_event():
    """Initialize background tasks on application startup."""
    logger.info("ShiftSync API starting up...")

    # Create tables if they don't exist (idempotent)
    from app.database import init_db, AsyncSessionLocal
    from sqlalchemy import text
    try:
        await init_db()
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        logger.info("Database connection verified, tables ready")
    except Exception as e:
        logger.error("Database connection failed at startup: %s", e)

    # Start cleanup scheduler
    if settings.environment == "production":
        start_cleanup_scheduler()
        logger.info("File cleanup scheduler started")
    else:
        logger.info("Cleanup scheduler disabled in development")

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(process.router, prefix="/api", tags=["process"])
app.include_router(download.router, prefix="/api", tags=["download"])
app.include_router(analytics.router, prefix="/api/internal", tags=["analytics"])
app.include_router(feedback.router, prefix="/api", tags=["feedback"])
app.include_router(payment.router, prefix="/api/payment", tags=["payment"])
app.include_router(health.router, tags=["health"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development"
    )

