"""
Secure logging configuration with sensitive data sanitization.
"""
import logging
import re
import sys
from typing import Optional

from app.config import settings


class SanitizingFormatter(logging.Formatter):
    """
    Formatter that redacts sensitive information from log messages.
    """
    
    # Patterns to redact
    SENSITIVE_PATTERNS = [
        # API keys
        (r'sk-[a-zA-Z0-9-]{20,}', 'sk-***REDACTED***'),
        (r'sk_live_[a-zA-Z0-9]{20,}', 'sk_live_***REDACTED***'),
        (r'sk_test_[a-zA-Z0-9]{20,}', 'sk_test_***REDACTED***'),
        
        # Database URLs
        (r'postgresql://[^@\s]+@', 'postgresql://***:***@'),
        (r'postgres://[^@\s]+@', 'postgres://***:***@'),
        
        # Azure connection strings
        (r'AccountKey=[^;]+', 'AccountKey=***REDACTED***'),
        (r'SharedAccessSignature=[^;]+', 'SharedAccessSignature=***REDACTED***'),
        
        # Generic secrets
        (r'"password"\s*:\s*"[^"]*"', '"password": "***REDACTED***"'),
        (r"'password'\s*:\s*'[^']*'", "'password': '***REDACTED***'"),
        (r'Bearer [a-zA-Z0-9._-]+', 'Bearer ***REDACTED***'),
        
        # Email addresses (partial redaction)
        (r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', r'***@\2'),
    ]
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with sensitive data redacted."""
        message = super().format(record)
        
        # Apply all redaction patterns
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            message = re.sub(pattern, replacement, message)
        
        return message


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Set up application logging with sanitization.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured root logger
    """
    # Get numeric level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatter
    formatter = SanitizingFormatter(
        fmt='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(numeric_level)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    
    return root_logger


def setup_sentry():
    """
    Initialize Sentry for error tracking and performance monitoring.
    Only activates if SENTRY_DSN is configured.
    """
    sentry_dsn = getattr(settings, 'sentry_dsn', None)
    
    if not sentry_dsn:
        logging.info("Sentry DSN not configured - error tracking disabled")
        return
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=settings.environment,
            
            # Performance monitoring
            traces_sample_rate=0.1 if settings.environment == "production" else 1.0,
            profiles_sample_rate=0.1 if settings.environment == "production" else 1.0,
            
            # Integrations
            integrations=[
                FastApiIntegration(
                    transaction_style="endpoint"
                ),
                SqlalchemyIntegration(),
            ],
            
            # Data scrubbing
            send_default_pii=False,  # Don't send IP addresses, etc.
            
            # Before send hook for additional sanitization
            before_send=sanitize_sentry_event,
        )
        
        logging.info("Sentry initialized successfully")
        
    except ImportError:
        logging.warning("sentry-sdk not installed - error tracking disabled")
    except Exception as e:
        logging.error(f"Failed to initialize Sentry: {e}")


def sanitize_sentry_event(event, hint):
    """
    Sanitize Sentry events before sending.
    Removes sensitive data that might leak through exceptions.
    """
    # Redact sensitive strings in exception messages
    if 'exception' in event:
        for exc in event['exception'].get('values', []):
            if exc.get('value'):
                for pattern, replacement in SanitizingFormatter.SENSITIVE_PATTERNS:
                    exc['value'] = re.sub(pattern, replacement, exc['value'])
    
    # Redact request data
    if 'request' in event:
        request = event['request']
        
        # Remove sensitive headers
        if 'headers' in request:
            sensitive_headers = ['authorization', 'cookie', 'x-api-key']
            for header in sensitive_headers:
                if header in request['headers']:
                    request['headers'][header] = '***REDACTED***'
        
        # Remove query string data
        if 'query_string' in request:
            request['query_string'] = '***REDACTED***'
    
    return event


# Create application logger
logger = logging.getLogger('shiftsync')
