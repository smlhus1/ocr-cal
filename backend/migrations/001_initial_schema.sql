-- Initial database schema for ShiftSync
-- GDPR-compliant: NO personal data stored
-- Auto-cleanup after 24h

-- Create extension for UUID support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Upload analytics table (anonymized metadata only)
CREATE TABLE IF NOT EXISTS upload_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- File metadata (anonymized)
    file_format VARCHAR(10) NOT NULL,  -- 'jpeg', 'png', 'pdf'
    file_size_kb INTEGER,
    
    -- OCR results (anonymized)
    ocr_engine VARCHAR(20),  -- 'tesseract', 'azure', etc.
    shifts_found INTEGER,
    confidence_score FLOAT,
    processing_time_ms INTEGER,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Error tracking (no personal data)
    error_type VARCHAR(50),
    
    -- Geography (country-level only, for stats)
    country_code CHAR(2),  -- ISO 3166-1 alpha-2 (e.g., 'NO', 'SE')
    
    -- Blob storage reference (for cleanup)
    blob_id VARCHAR(100),
    expires_at TIMESTAMP NOT NULL  -- Auto-delete after 24h
);

-- Indexes for performance
CREATE INDEX idx_created_at ON upload_analytics(created_at);
CREATE INDEX idx_expires_at ON upload_analytics(expires_at);
CREATE INDEX idx_file_format ON upload_analytics(file_format);
CREATE INDEX idx_success ON upload_analytics(success);

-- Feedback log table (anonymized user corrections)
CREATE TABLE IF NOT EXISTS feedback_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Reference to upload (for correlation, not identification)
    upload_id UUID NOT NULL,
    
    -- Error type classification
    error_type VARCHAR(50) NOT NULL,  -- 'wrong_date', 'missing_shift', 'wrong_time', etc.
    
    -- Anonymized correction pattern (JSON-like string)
    -- Example: "expected_DD.MM.YYYY_got_MM/DD/YYYY"
    correction_pattern VARCHAR(500)
);

-- Index for feedback analysis
CREATE INDEX idx_feedback_error_type ON feedback_log(error_type);
CREATE INDEX idx_feedback_created_at ON feedback_log(created_at);

-- Function to auto-delete expired records
CREATE OR REPLACE FUNCTION cleanup_expired_records()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM upload_analytics
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE upload_analytics IS 'Anonymized upload analytics - GDPR compliant, auto-delete after 24h';
COMMENT ON TABLE feedback_log IS 'Anonymized user feedback for ML improvements';
COMMENT ON COLUMN upload_analytics.country_code IS 'Country-level geography only (from IP), never store full IP';
COMMENT ON COLUMN upload_analytics.blob_id IS 'Reference for blob storage cleanup, not file content';

