"""
Configuration management with Pydantic Settings.
Supports loading from .env file and Azure Key Vault in production.
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Environment
    environment: str = "development"
    
    # FastAPI
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Database
    database_url: str
    
    # Tesseract OCR
    tesseract_path: str = "/usr/bin/tesseract"
    ocr_language: str = "nor"
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    
    # Azure Storage
    azure_storage_connection_string: Optional[str] = None
    azure_storage_container_name: str = "shiftsync-uploads"
    
    # Azure Key Vault
    key_vault_url: Optional[str] = None
    
    # Azure Application Insights
    azure_application_insights_key: Optional[str] = None
    
    # Stripe
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    
    # Security
    secret_salt: str
    internal_api_key: Optional[str] = None  # API key for internal endpoints

    @field_validator('secret_salt')
    @classmethod
    def validate_secret_salt(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                'SECRET_SALT must be at least 32 characters. '
                'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        return v
    
    # Dev bypass quota (must be explicitly enabled)
    dev_bypass_quota: bool = False

    # Rate Limiting
    rate_limit_per_minute: int = 10
    
    # File Upload
    max_file_size_mb: int = 10
    
    # Application Insights
    applicationinsights_connection_string: Optional[str] = None
    
    # Sentry
    sentry_dsn: Optional[str] = None
    
    # Frontend URL (for CORS)
    frontend_url: str = "http://localhost:3000"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Load from Azure Key Vault in production
        if self.environment == "production" and self.key_vault_url:
            self._load_from_keyvault()
    
    def _load_from_keyvault(self):
        """Load secrets from Azure Key Vault in production."""
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            
            credential = DefaultAzureCredential()
            client = SecretClient(
                vault_url=self.key_vault_url,
                credential=credential
            )
            
            # Load secrets
            if not self.stripe_secret_key:
                self.stripe_secret_key = client.get_secret("STRIPE-SECRET-KEY").value
            if not self.database_url:
                self.database_url = client.get_secret("DATABASE-URL").value
            if not self.azure_storage_connection_string:
                self.azure_storage_connection_string = client.get_secret("AZURE-STORAGE-CONNECTION-STRING").value
                
        except Exception as e:
            import logging
            logging.getLogger('shiftsync').error(f"Could not load from Key Vault: {e}")


# Global settings instance
settings = Settings()

