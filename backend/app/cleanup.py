"""
Automatic cleanup job for expired files and database records.
Runs hourly to delete files older than 24 hours.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import settings
from app.database import cleanup_expired_records

logger = logging.getLogger('shiftsync.cleanup')


async def cleanup_old_files():
    """
    Delete files older than 24 hours from local storage.
    """
    uploads_dir = Path("uploads")
    if not uploads_dir.exists():
        return 0

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
    deleted_count = 0

    for file_path in uploads_dir.iterdir():
        if file_path.is_file():
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)

            if mtime < cutoff_time:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug("Deleted expired file: %s", file_path.name)
                except Exception as e:
                    logger.error("Failed to delete %s: %s", file_path.name, e)

    return deleted_count


async def cleanup_blob_storage():
    """
    Delete expired files from Azure Blob Storage.
    """
    if not settings.azure_storage_connection_string:
        return 0

    try:
        from app.storage.blob_storage import get_storage_service
        storage = get_storage_service()
        if hasattr(storage, 'cleanup_expired'):
            count = await storage.cleanup_expired()
            return count
    except Exception as e:
        logger.error("Blob storage cleanup failed: %s", e)

    return 0


async def cleanup_expired_db_records():
    """
    Delete expired records from database.
    """
    try:
        count = await cleanup_expired_records()
        return count
    except Exception as e:
        logger.error("Database cleanup failed: %s", e)
        return 0


async def run_cleanup():
    """
    Run full cleanup: files, blob storage, and database records.
    """
    logger.info("Starting scheduled cleanup...")

    files_deleted = await cleanup_old_files()
    logger.info("Deleted %d expired local files", files_deleted)

    blobs_deleted = await cleanup_blob_storage()
    logger.info("Deleted %d expired blobs", blobs_deleted)

    records_deleted = await cleanup_expired_db_records()
    logger.info("Deleted %d expired database records", records_deleted)

    logger.info("Cleanup complete")

    return files_deleted, blobs_deleted, records_deleted


async def schedule_cleanup(interval_seconds: int = 3600):
    """
    Schedule cleanup to run periodically.
    """
    logger.info("Cleanup scheduler started (interval: %ds)", interval_seconds)

    while True:
        try:
            await run_cleanup()
        except Exception as e:
            logger.error("Cleanup job failed: %s", e)

        await asyncio.sleep(interval_seconds)


def start_cleanup_scheduler():
    """
    Start the cleanup scheduler as a background task.
    """
    asyncio.create_task(schedule_cleanup())
    logger.info("Cleanup scheduler initialized")
