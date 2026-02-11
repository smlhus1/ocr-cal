"""
Security tests for ShiftSync API.
Tests for SQL injection, XSS, file upload vulnerabilities, rate limiting, etc.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import io

# Import with mock settings
import sys
sys.path.insert(0, '..')


class TestSQLInjection:
    """Tests for SQL injection prevention."""
    
    def test_upload_id_injection(self, client):
        """Test that SQL injection in upload_id is blocked."""
        # Attempt SQL injection via upload_id
        malicious_ids = [
            "'; DROP TABLE upload_analytics; --",
            "1 OR 1=1",
            "1; DELETE FROM users WHERE 1=1",
            "1 UNION SELECT * FROM users",
            "' OR '1'='1",
        ]
        
        for malicious_id in malicious_ids:
            response = client.post("/api/process", json={
                "upload_id": malicious_id
            })
            # Should be rejected by validation (not 500 server error)
            assert response.status_code in [400, 422], f"Potential SQL injection: {malicious_id}"
    
    def test_analytics_days_injection(self, client, api_key_header):
        """Test that SQL injection via days parameter is blocked."""
        response = client.get(
            "/api/internal/analytics?days=7; DROP TABLE users",
            headers=api_key_header
        )
        assert response.status_code in [400, 422]


class TestXSSPrevention:
    """Tests for XSS prevention."""
    
    def test_owner_name_xss(self, client):
        """Test that XSS in owner_name is sanitized."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "'-alert('xss')-'",
        ]
        
        for payload in xss_payloads:
            response = client.post("/api/generate-calendar", json={
                "shifts": [
                    {
                        "date": "01.01.2024",
                        "start_time": "08:00",
                        "end_time": "16:00",
                        "shift_type": "tidlig"
                    }
                ],
                "owner_name": payload
            })
            
            if response.status_code == 200:
                # Check that XSS payload is not in response
                content = response.content.decode('utf-8')
                assert '<script>' not in content.lower()
                assert 'javascript:' not in content.lower()
                assert 'onerror=' not in content.lower()


class TestFileUploadSecurity:
    """Tests for file upload security."""
    
    def test_reject_exe_file(self, client):
        """Test that executable files are rejected."""
        # Create fake exe content
        exe_content = b'MZ' + b'\x00' * 100  # PE header signature
        
        response = client.post(
            "/api/upload",
            files={"file": ("malware.exe", io.BytesIO(exe_content), "application/x-msdownload")}
        )
        assert response.status_code in [400, 415]
    
    def test_reject_oversized_file(self, client):
        """Test that files over 10MB are rejected."""
        large_content = b'0' * (11 * 1024 * 1024)  # 11MB
        
        response = client.post(
            "/api/upload",
            files={"file": ("large.jpg", io.BytesIO(large_content), "image/jpeg")}
        )
        assert response.status_code == 413
    
    def test_reject_fake_extension(self, client):
        """Test that files with mismatched content are rejected."""
        # Create file with .jpg extension but PNG content
        png_header = bytes([0x89, 0x50, 0x4E, 0x47])  # PNG magic bytes
        
        response = client.post(
            "/api/upload",
            files={"file": ("image.jpg", io.BytesIO(png_header + b'\x00' * 100), "image/jpeg")}
        )
        # Should be rejected due to signature mismatch
        assert response.status_code in [400, 415]


class TestRateLimiting:
    """Tests for rate limiting."""
    
    def test_upload_rate_limit(self, client):
        """Test that upload endpoint is rate limited."""
        # Create minimal valid JPEG
        jpeg_content = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b'\x00' * 100
        
        # Make 15 requests (limit is 10/minute)
        responses = []
        for i in range(15):
            response = client.post(
                "/api/upload",
                files={"file": (f"test{i}.jpg", io.BytesIO(jpeg_content), "image/jpeg")}
            )
            responses.append(response.status_code)
        
        # At least some should be rate limited (429)
        assert 429 in responses, "Rate limiting not working"


class TestAuthenticationSecurity:
    """Tests for authentication security."""
    
    def test_internal_api_requires_key(self, client):
        """Test that internal API requires API key."""
        response = client.get("/api/internal/analytics")
        assert response.status_code in [401, 403]
    
    def test_internal_api_rejects_wrong_key(self, client):
        """Test that internal API rejects wrong key."""
        response = client.get(
            "/api/internal/analytics",
            headers={"X-API-Key": "wrong_key_12345"}
        )
        assert response.status_code == 403
    
    def test_internal_api_accepts_correct_key(self, client, api_key_header):
        """Test that internal API accepts correct key."""
        response = client.get(
            "/api/internal/analytics",
            headers=api_key_header
        )
        assert response.status_code == 200


class TestInputValidation:
    """Tests for input validation."""
    
    def test_invalid_uuid_format(self, client):
        """Test that invalid UUID format is rejected."""
        response = client.post("/api/process", json={
            "upload_id": "not-a-valid-uuid"
        })
        assert response.status_code == 422
    
    def test_invalid_shift_data(self, client):
        """Test that invalid shift data is rejected."""
        response = client.post("/api/generate-calendar", json={
            "shifts": [
                {
                    "date": "invalid-date",
                    "start_time": "25:00",  # Invalid time
                    "end_time": "99:99",
                    "shift_type": "invalid_type"
                }
            ],
            "owner_name": "Test User"
        })
        # Should handle gracefully, not crash
        assert response.status_code in [200, 400, 422]


class TestSecurityHeaders:
    """Tests for security headers."""
    
    def test_security_headers_present(self, client):
        """Test that security headers are set."""
        response = client.get("/health")
        
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert "Strict-Transport-Security" in response.headers
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


class TestCORS:
    """Tests for CORS configuration."""
    
    def test_cors_restricts_origin(self, client):
        """Test that CORS restricts unauthorized origins."""
        response = client.options(
            "/api/upload",
            headers={
                "Origin": "https://evil-site.com",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        # Should not include evil origin in allowed origins
        allowed_origin = response.headers.get("Access-Control-Allow-Origin", "")
        assert "evil-site.com" not in allowed_origin


# Fixtures
@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    # Mock settings
    with patch('app.config.settings') as mock_settings:
        mock_settings.environment = "testing"
        mock_settings.secret_salt = "test_salt"
        mock_settings.internal_api_key = "test_api_key_12345"
        mock_settings.database_url = "sqlite:///:memory:"
        mock_settings.max_file_size_mb = 10
        mock_settings.rate_limit_per_minute = 10
        mock_settings.frontend_url = "http://localhost:3000"
        
        from app.main import app
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture
def api_key_header():
    """Return valid API key header."""
    return {"X-API-Key": "test_api_key_12345"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
