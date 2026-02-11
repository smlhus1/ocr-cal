"""
Blob storage management for uploaded files.
Supports Azure Blob Storage with 24h auto-expiry.
"""
import logging
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from azure.storage.blob import BlobServiceClient, BlobClient, generate_blob_sas, BlobSasPermissions

from app.config import settings

logger = logging.getLogger('shiftsync')


class BlobStorageService:
    """Service for managing file uploads in Azure Blob Storage."""
    
    CONTAINER_NAME = "shift-uploads"
    
    def __init__(self):
        """Initialize blob storage client."""
        if not settings.azure_storage_connection_string:
            raise ValueError("Azure Storage connection string not configured")
        
        self.blob_service_client = BlobServiceClient.from_connection_string(
            settings.azure_storage_connection_string
        )
        
        # Ensure container exists
        self._ensure_container()
    
    def _ensure_container(self):
        """Create container if it doesn't exist."""
        try:
            container_client = self.blob_service_client.get_container_client(self.CONTAINER_NAME)
            if not container_client.exists():
                container_client.create_container()
        except Exception as e:
            logger.warning(f"Could not ensure container exists: {e}")
    
    async def upload_file(self, upload_id: str, file_content: bytes, content_type: str) -> str:
        """
        Upload file to blob storage.
        
        Args:
            upload_id: Unique upload identifier (UUID)
            file_content: File content as bytes
            content_type: MIME type (image/jpeg, image/png, application/pdf)
            
        Returns:
            Blob URL
        """
        # Determine file extension
        ext_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "application/pdf": ".pdf"
        }
        extension = ext_map.get(content_type, ".bin")
        
        # Blob name with extension
        blob_name = f"{upload_id}{extension}"
        
        # Get blob client
        blob_client = self.blob_service_client.get_blob_client(
            container=self.CONTAINER_NAME,
            blob=blob_name
        )
        
        # Upload with metadata
        metadata = {
            "upload_id": upload_id,
            "content_type": content_type,
            "uploaded_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        
        blob_client.upload_blob(
            file_content,
            overwrite=True,
            content_settings={
                "content_type": content_type
            },
            metadata=metadata
        )
        
        return blob_client.url
    
    async def download_file(self, upload_id: str) -> Optional[str]:
        """
        Download file from blob storage to temp file.
        
        Args:
            upload_id: Upload identifier
            
        Returns:
            Path to temporary file, or None if not found
        """
        # Try different extensions
        for ext in [".jpg", ".png", ".pdf"]:
            blob_name = f"{upload_id}{ext}"
            blob_client = self.blob_service_client.get_blob_client(
                container=self.CONTAINER_NAME,
                blob=blob_name
            )
            
            if blob_client.exists():
                # Download to temp file
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=ext
                )
                
                with open(temp_file.name, "wb") as f:
                    blob_data = blob_client.download_blob()
                    f.write(blob_data.readall())
                
                return temp_file.name
        
        return None
    
    async def delete_file(self, upload_id: str) -> bool:
        """
        Delete file from blob storage.
        
        Args:
            upload_id: Upload identifier
            
        Returns:
            True if deleted, False if not found
        """
        # Try different extensions
        deleted = False
        for ext in [".jpg", ".png", ".pdf"]:
            blob_name = f"{upload_id}{ext}"
            blob_client = self.blob_service_client.get_blob_client(
                container=self.CONTAINER_NAME,
                blob=blob_name
            )
            
            if blob_client.exists():
                blob_client.delete_blob()
                deleted = True
        
        return deleted
    
    async def cleanup_expired(self) -> int:
        """
        Delete expired blobs (24h+).
        Should be run as scheduled job.
        
        Returns:
            Number of blobs deleted
        """
        container_client = self.blob_service_client.get_container_client(self.CONTAINER_NAME)
        
        deleted_count = 0
        now = datetime.utcnow()
        
        # List all blobs
        blob_list = container_client.list_blobs(include=['metadata'])
        
        for blob in blob_list:
            # Check if expired
            if blob.metadata and 'expires_at' in blob.metadata:
                expires_at = datetime.fromisoformat(blob.metadata['expires_at'])
                if expires_at < now:
                    blob_client = container_client.get_blob_client(blob.name)
                    blob_client.delete_blob()
                    deleted_count += 1
        
        return deleted_count


# Local file storage fallback (for development without Azure)
class LocalFileStorage:
    """Local filesystem storage for development."""
    
    UPLOAD_DIR = Path("uploads")
    
    def __init__(self):
        """Initialize local storage."""
        self.UPLOAD_DIR.mkdir(exist_ok=True)
    
    async def upload_file(self, upload_id: str, file_content: bytes, content_type: str) -> str:
        """Upload file to local storage."""
        ext_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "application/pdf": ".pdf"
        }
        extension = ext_map.get(content_type, ".bin")
        
        file_path = self.UPLOAD_DIR / f"{upload_id}{extension}"
        
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        return str(file_path)
    
    async def download_file(self, upload_id: str) -> Optional[str]:
        """Download (copy to temp file) local file."""
        for ext in [".jpg", ".png", ".pdf"]:
            file_path = self.UPLOAD_DIR / f"{upload_id}{ext}"
            if file_path.exists():
                # Create a temporary copy so the original isn't deleted by cleanup
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=ext
                )
                
                with open(file_path, "rb") as source:
                    with open(temp_file.name, "wb") as dest:
                        dest.write(source.read())
                
                return temp_file.name
        return None
    
    async def delete_file(self, upload_id: str) -> bool:
        """Delete local file."""
        for ext in [".jpg", ".png", ".pdf"]:
            file_path = self.UPLOAD_DIR / f"{upload_id}{ext}"
            if file_path.exists():
                file_path.unlink()
                return True
        return False
    
    async def cleanup_expired(self) -> int:
        """Cleanup files older than 24h."""
        deleted_count = 0
        now = datetime.utcnow().timestamp()
        
        for file_path in self.UPLOAD_DIR.glob("*"):
            if file_path.is_file():
                # Check if older than 24h
                age = now - file_path.stat().st_mtime
                if age > 24 * 3600:
                    file_path.unlink()
                    deleted_count += 1
        
        return deleted_count


# Factory function to get storage service
def get_storage_service():
    """Get storage service based on environment."""
    if settings.environment == "production" and settings.azure_storage_connection_string:
        return BlobStorageService()
    else:
        # Use local storage for development
        return LocalFileStorage()

