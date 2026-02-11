#!/bin/bash
#
# ShiftSync Database Backup Script
# Performs PostgreSQL backup with compression and optional upload to Azure Blob
#
# Usage:
#   ./backup_database.sh [--upload] [--keep-days 7]
#
# Environment variables required:
#   DATABASE_URL - PostgreSQL connection string
#   AZURE_STORAGE_CONNECTION_STRING - (optional) for cloud backup
#

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/backups/shiftsync}"
KEEP_DAYS="${KEEP_DAYS:-7}"
UPLOAD_TO_AZURE=false
AZURE_CONTAINER="shiftsync-backups"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --upload)
            UPLOAD_TO_AZURE=true
            shift
            ;;
        --keep-days)
            KEEP_DAYS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Timestamp for backup file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="shiftsync_backup_${TIMESTAMP}.sql.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "=== ShiftSync Database Backup ==="
echo "Timestamp: $TIMESTAMP"
echo "Backup dir: $BACKUP_DIR"

# Check DATABASE_URL
if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL environment variable not set"
    exit 1
fi

# Parse DATABASE_URL for pg_dump
# Format: postgresql://user:password@host:port/database
DB_HOST=$(echo $DATABASE_URL | sed -E 's/.*@([^:]+).*/\1/')
DB_PORT=$(echo $DATABASE_URL | sed -E 's/.*:([0-9]+)\/.*/\1/')
DB_NAME=$(echo $DATABASE_URL | sed -E 's/.*\/([^?]+).*/\1/')
DB_USER=$(echo $DATABASE_URL | sed -E 's/.*:\/\/([^:]+).*/\1/')

echo "Database: $DB_NAME @ $DB_HOST:$DB_PORT"

# Perform backup
echo "Starting backup..."
pg_dump \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --format=custom \
    --compress=9 \
    --file="$BACKUP_DIR/$BACKUP_FILE" \
    --verbose

# Verify backup
BACKUP_SIZE=$(ls -lh "$BACKUP_DIR/$BACKUP_FILE" | awk '{print $5}')
echo "Backup completed: $BACKUP_FILE ($BACKUP_SIZE)"

# Upload to Azure if requested
if [ "$UPLOAD_TO_AZURE" = true ]; then
    echo "Uploading to Azure Blob Storage..."
    
    if [ -z "${AZURE_STORAGE_CONNECTION_STRING:-}" ]; then
        echo "WARNING: AZURE_STORAGE_CONNECTION_STRING not set, skipping upload"
    else
        az storage blob upload \
            --container-name "$AZURE_CONTAINER" \
            --name "$BACKUP_FILE" \
            --file "$BACKUP_DIR/$BACKUP_FILE" \
            --connection-string "$AZURE_STORAGE_CONNECTION_STRING"
        
        echo "Upload complete!"
    fi
fi

# Cleanup old backups
echo "Cleaning up backups older than $KEEP_DAYS days..."
find "$BACKUP_DIR" -name "shiftsync_backup_*.sql.gz" -mtime +$KEEP_DAYS -delete
REMAINING=$(ls -1 "$BACKUP_DIR"/shiftsync_backup_*.sql.gz 2>/dev/null | wc -l)
echo "Remaining local backups: $REMAINING"

echo "=== Backup Complete ==="
