"""
FastAPI main application with security middleware and routing.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import time

from app.config import settings
from app.security import limiter
from app.logging_config import setup_logging, setup_sentry, logger

app_logger = logging.getLogger('shiftsync')

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

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    allow_credentials=False,  # No cookies used
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],  # Removed Authorization - not used
    max_age=3600,
)


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
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000  # Convert to ms
    response.headers["X-Process-Time-Ms"] = str(int(process_time))
    
    # Audit log (sanitized - no personal data)
    logger.info(
        f"AUDIT | {request.method} {request.url.path} | "
        f"client={client_id} | status={response.status_code} | "
        f"time={int(process_time)}ms"
    )
    
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return a safe error response."""
    app_logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
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

