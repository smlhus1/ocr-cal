"""
Security utilities including rate limiting, CORS, and file validation.
"""
import hashlib
import logging

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
limiter = Limiter(key_func=get_composite_key)


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


async def validate_file(file: UploadFile) -> None:
    """
    Validate uploaded file:
    - Check size
    - Check MIME type
    - Validate file signature (magic bytes)
    """
    # Check file size
    content = await file.read()
    file_size = len(content)
    await file.seek(0)  # Reset file pointer
    
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
        logger.error(f"python-magic failed, rejecting file: {e}")
        raise HTTPException(
            status_code=400,
            detail="Could not determine file type. Please try again."
        )
    
    allowed_types = ["image/jpeg", "image/png", "application/pdf"]
    if file_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file_type}. Allowed: {', '.join(allowed_types)}"
        )
    
    # Validate file signature (magic bytes)
    if not validate_file_signature(content, file_type):
        raise HTTPException(
            status_code=400,
            detail="File signature does not match declared type. Possible file corruption or security risk."
        )


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
    Scan file for malware using ClamAV.
    Returns True if file is safe, False if malware detected.
    
    Raises:
        RuntimeError: If ClamAV is not available
    """
    try:
        import clamd
        
        # Try Unix socket first (Docker), then network
        try:
            cd = clamd.ClamdUnixSocket('/var/run/clamav/clamd.ctl')
            cd.ping()
        except (clamd.ConnectionError, FileNotFoundError):
            try:
                cd = clamd.ClamdNetworkSocket(host='localhost', port=3310)
                cd.ping()
            except clamd.ConnectionError:
                # ClamAV not running - fail open in development, closed in production
                if settings.environment == "development":
                    logger.warning("ClamAV not available - skipping scan in development")
                    return True
                else:
                    raise RuntimeError("ClamAV scanner not available in production")
        
        # Scan the file
        result = cd.scan(file_path)
        
        if result is None:
            return True  # No result means clean
        
        # Check result for this file
        file_result = result.get(file_path)
        if file_result is None:
            return True
        
        status, signature = file_result
        if status == 'OK':
            return True
        elif status == 'FOUND':
            logger.warning(f"Malware detected: {signature}")
            return False
        else:
            logger.error(f"ClamAV error: {status}")
            return False
            
    except ImportError:
        # clamd not installed - allow in dev, block in production
        if settings.environment == "development":
            logger.warning("clamd not installed - skipping scan")
            return True
        else:
            raise RuntimeError("Malware scanning not configured")
    except Exception as e:
        logger.error(f"Malware scan error: {e}")
        # Fail closed in production
        if settings.environment == "production":
            return False
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

