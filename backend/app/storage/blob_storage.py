"""
Blob storage management for uploaded files.
Supports Azure Blob Storage with 24h auto-expiry.
"""
import asyncio
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from azure.storage.blob import BlobServiceClient, BlobClient, generate_blob_sas, BlobSasPermissions

from app.config import settings
from app.models import MIME_TO_EXTENSION

logger = logging.getLogger('shiftsync')


class BlobStorageService:
    """Service for managing file uploads in Azure Blob Storage."""

    def __init__(self):
        """Initialize blob storage client."""
        if not settings.azure_storage_connection_string:
            raise ValueError("Azure Storage connection string not configured")

        self.container_name = settings.azure_storage_container_name

        self.blob_service_client = BlobServiceClient.from_connection_string(
            settings.azure_storage_connection_string
        )

        # Ensure container exists
        self._ensure_container()

    def _ensure_container(self):
        """Create container if it doesn't exist."""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            if not container_client.exists():
                container_client.create_container()
        except Exception as e:
            logger.warning("Could not ensure container exists: %s", e)

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
        extension = MIME_TO_EXTENSION.get(content_type, ".bin")
        blob_name = f"{upload_id}{extension}"

        now = datetime.now(timezone.utc)
        metadata = {
            "upload_id": upload_id,
            "content_type": content_type,
            "uploaded_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=24)).isoformat()
        }

        def _upload():
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                content_settings={"content_type": content_type},
                metadata=metadata
            )
            return blob_client.url

        return await asyncio.to_thread(_upload)

    async def download_file(self, upload_id: str) -> Optional[str]:
        """
        Download file from blob storage to temp file.

        Args:
            upload_id: Upload identifier

        Returns:
            Path to temporary file, or None if not found
        """
        def _download():
            for ext in [".jpg", ".png", ".pdf"]:
                blob_name = f"{upload_id}{ext}"
                blob_client = self.blob_service_client.get_blob_client(
                    container=self.container_name,
                    blob=blob_name
                )
                if blob_client.exists():
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                    with open(temp_file.name, "wb") as f:
                        blob_data = blob_client.download_blob()
                        f.write(blob_data.readall())
                    return temp_file.name
            return None

        return await asyncio.to_thread(_download)

    async def get_file_path(self, upload_id: str) -> Optional[str]:
        """
        Get a local file path for a blob (downloads to temp file).

        Args:
            upload_id: Upload identifier

        Returns:
            Path to temporary file, or None if not found
        """
        return await self.download_file(upload_id)

    async def delete_file(self, upload_id: str) -> bool:
        """
        Delete file from blob storage.

        Args:
            upload_id: Upload identifier

        Returns:
            True if deleted, False if not found
        """
        def _delete():
            deleted = False
            for ext in [".jpg", ".png", ".pdf"]:
                blob_name = f"{upload_id}{ext}"
                blob_client = self.blob_service_client.get_blob_client(
                    container=self.container_name,
                    blob=blob_name
                )
                if blob_client.exists():
                    blob_client.delete_blob()
                    deleted = True
            return deleted

        return await asyncio.to_thread(_delete)

    async def cleanup_expired(self) -> int:
        """
        Delete expired blobs (24h+).
        Should be run as scheduled job.

        Returns:
            Number of blobs deleted
        """
        def _cleanup():
            container_client = self.blob_service_client.get_container_client(self.container_name)
            deleted_count = 0
            now = datetime.now(timezone.utc)

            blob_list = container_client.list_blobs(include=['metadata'])
            for blob in blob_list:
                if blob.metadata and 'expires_at' in blob.metadata:
                    expires_at = datetime.fromisoformat(blob.metadata['expires_at'])
                    if expires_at < now:
                        blob_client = container_client.get_blob_client(blob.name)
                        blob_client.delete_blob()
                        deleted_count += 1
            return deleted_count

        return await asyncio.to_thread(_cleanup)


# Local file storage fallback (for development without Azure)
class LocalFileStorage:
    """Local filesystem storage for development."""

    UPLOAD_DIR = Path("uploads")

    def __init__(self):
        """Initialize local storage."""
        self.UPLOAD_DIR.mkdir(exist_ok=True)

    async def upload_file(self, upload_id: str, file_content: bytes, content_type: str) -> str:
        """Upload file to local storage."""
        extension = MIME_TO_EXTENSION.get(content_type, ".bin")
        file_path = self.UPLOAD_DIR / f"{upload_id}{extension}"

        with open(file_path, "wb") as f:
            f.write(file_content)

        return str(file_path)

    async def download_file(self, upload_id: str) -> Optional[str]:
        """Download (copy to temp file) local file."""
        for ext in [".jpg", ".png", ".pdf"]:
            file_path = self.UPLOAD_DIR / f"{upload_id}{ext}"
            if file_path.exists():
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                with open(file_path, "rb") as source:
                    with open(temp_file.name, "wb") as dest:
                        dest.write(source.read())
                return temp_file.name
        return None

    async def get_file_path(self, upload_id: str) -> Optional[str]:
        """Get direct file path for local storage."""
        for ext in [".jpg", ".png", ".pdf"]:
            file_path = self.UPLOAD_DIR / f"{upload_id}{ext}"
            if file_path.exists():
                return str(file_path)
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
        now = datetime.now(timezone.utc).timestamp()

        for file_path in self.UPLOAD_DIR.glob("*"):
            if file_path.is_file():
                age = now - file_path.stat().st_mtime
                if age > 24 * 3600:
                    file_path.unlink()
                    deleted_count += 1

        return deleted_count


# Singleton storage instance
_storage_instance = None


def get_storage_service():
    """Get storage service based on environment (singleton)."""
    global _storage_instance
    if _storage_instance is None:
        if settings.environment == "production" and settings.azure_storage_connection_string:
            _storage_instance = BlobStorageService()
        else:
            _storage_instance = LocalFileStorage()
    return _storage_instance
