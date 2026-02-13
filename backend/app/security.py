"""
Security utilities including rate limiting, CORS, and file validation.
"""
import hashlib
import hmac
import logging
import time

import magic
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request, HTTPException, UploadFile
from typing import Optional
from app.config import settings

logger = logging.getLogger('shiftsync')


def get_composite_key(request: Request) -> str:
    """
    Generate composite key for rate limiting.
    Combines IP + User-Agent hash to make VPN bypass harder.
    """
    ip = get_remote_address(request)
    user_agent = request.headers.get('user-agent', 'unknown')
    
    # Create composite key
    composite = f"{ip}:{hashlib.md5(user_agent.encode()).hexdigest()[:8]}"
    return composite


# Rate limiter instance with composite key
# Disable rate limiting in development for easier testing
limiter = Limiter(
    key_func=get_composite_key,
    enabled=settings.environment != "development",
)


def get_user_identifier(request: Request) -> str:
    """
    Generate anonymous user identifier from IP address.
    Uses SHA256 hash with salt for privacy.
    """
    ip = get_remote_address(request)
    identifier = hashlib.sha256(
        f"{ip}{settings.secret_salt}".encode()
    ).hexdigest()[:16]
    return identifier


# Download token expiry in seconds (10 minutes)
DOWNLOAD_TOKEN_EXPIRY = 600


def generate_download_token(upload_id: str) -> str:
    """
    Generate HMAC-signed download token for a specific upload.
    Token includes expiry timestamp and is signed with SECRET_SALT.

    Args:
        upload_id: The upload ID to authorize download for

    Returns:
        Signed token string in format "expiry:signature"
    """
    expiry = int(time.time()) + DOWNLOAD_TOKEN_EXPIRY
    message = f"{upload_id}:{expiry}".encode()
    signature = hmac.new(
        settings.secret_salt.encode(), message, hashlib.sha256
    ).hexdigest()
    return f"{expiry}:{signature}"


def validate_download_token(upload_id: str, token: str) -> None:
    """
    Validate HMAC-signed download token.

    Args:
        upload_id: The upload ID the token should authorize
        token: The token string to verify

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        expiry_str, signature = token.split(":", 1)
        expiry = int(expiry_str)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=403, detail="Invalid download token")

    # Check expiry
    if time.time() > expiry:
        raise HTTPException(status_code=403, detail="Download token expired")

    # Verify signature
    message = f"{upload_id}:{expiry}".encode()
    expected = hmac.new(
        settings.secret_salt.encode(), message, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=403, detail="Invalid download token")


async def validate_file(file: UploadFile) -> bytes:
    """
    Validate uploaded file and return its content.
    - Check size
    - Check MIME type
    - Validate file signature (magic bytes)

    Returns:
        File content as bytes (avoids double-read).
    """
    from app.models import ALLOWED_MIME_TYPES

    content = await file.read()
    file_size = len(content)

    max_size = settings.max_file_size_mb * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB"
        )

    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty"
        )

    # Validate MIME type from content (not just extension)
    try:
        file_type = magic.from_buffer(content, mime=True)
    except Exception as e:
        logger.error("python-magic failed, rejecting file: %s", e)
        raise HTTPException(
            status_code=400,
            detail="Could not determine file type. Please try again."
        )

    if file_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file_type}. Allowed: {', '.join(ALLOWED_MIME_TYPES)}"
        )

    # Validate file signature (magic bytes)
    if not validate_file_signature(content, file_type):
        raise HTTPException(
            status_code=400,
            detail="File signature does not match declared type. Possible file corruption or security risk."
        )

    return content


def validate_file_signature(content: bytes, mime_type: str) -> bool:
    """
    Validate file signature against known magic bytes.
    Prevents files with fake extensions.
    """
    if len(content) < 4:
        return False
    
    # Get first 4 bytes as hex
    header = content[:4].hex()
    
    # Known file signatures
    signatures = {
        'image/jpeg': ['ffd8ffe0', 'ffd8ffe1', 'ffd8ffe2', 'ffd8ffe3'],
        'image/png': ['89504e47'],
        'application/pdf': ['25504446']
    }
    
    expected_sigs = signatures.get(mime_type, [])
    return any(header.startswith(sig) for sig in expected_sigs)


async def scan_file_for_malware(file_path: str) -> bool:
    """
    Placeholder for malware scanning.
    Files are already validated via magic bytes + file signatures.
    All uploads auto-delete after 24h.

    Returns True (safe) always - ClamAV removed for MVP to reduce image size.
    """
    logger.debug("Malware scan skipped (ClamAV removed for MVP)")
    return True


def get_country_code(request: Request) -> Optional[str]:
    """
    Extract country code from request for analytics.
    Uses CloudFlare headers or GeoIP lookup.
    Returns None if cannot determine.
    """
    # Try CloudFlare header first (if using CF)
    country = request.headers.get('CF-IPCountry')
    if country and country != 'XX':
        return country
    
    # Try other common headers
    country = request.headers.get('X-Country-Code')
    if country:
        return country
    
    # TODO: Implement GeoIP lookup for production
    # For MVP, return None to avoid logging
    return None

