# Backup and Restore Guide for ShiftSync

## Overview

ShiftSync uses PostgreSQL for metadata storage. This guide covers backup procedures, restore processes, and disaster recovery.

## Backup Strategy

### What Gets Backed Up

| Data Type | Storage | Backup Method | Retention |
|-----------|---------|---------------|-----------|
| Database (metadata) | PostgreSQL | pg_dump | 7 days local, 30 days Azure |
| Uploaded files | Blob Storage | Auto-deleted after 24h | N/A |
| Configuration | Key Vault | Azure-managed | Indefinite |

### Backup Schedule

**Recommended:**
- **Hourly**: PostgreSQL auto-backup (Azure managed)
- **Daily**: Full database export with `backup_database.sh`
- **Weekly**: Offsite backup verification

## Local Backup

### Manual Backup

```bash
# Set environment
export DATABASE_URL="postgresql://user:pass@localhost:5432/shiftsync"

# Run backup script
cd backend/scripts
chmod +x backup_database.sh
./backup_database.sh

# With Azure upload
./backup_database.sh --upload

# Keep backups longer
./backup_database.sh --keep-days 14
```

### Automated Backup (Cron)

Add to crontab (`crontab -e`):

```bash
# Daily backup at 2 AM
0 2 * * * /app/scripts/backup_database.sh --upload >> /var/log/backup.log 2>&1

# Weekly full backup on Sunday at 3 AM
0 3 * * 0 /app/scripts/backup_database.sh --upload --keep-days 30 >> /var/log/backup.log 2>&1
```

## Azure PostgreSQL Backups

Azure Database for PostgreSQL Flexible Server provides automatic backups:

### Point-in-Time Recovery (PITR)

```bash
# Restore to specific timestamp
az postgres flexible-server restore \
  --resource-group shiftsync-rg \
  --name shiftsync-db-restored \
  --source-server shiftsync-db \
  --restore-point-in-time "2024-01-15T14:30:00Z"
```

### Geo-Redundant Restore

```bash
# Restore from geo-redundant backup (disaster recovery)
az postgres flexible-server geo-restore \
  --resource-group shiftsync-rg \
  --name shiftsync-db-dr \
  --source-server shiftsync-db \
  --location westeurope
```

## Restore Procedures

### Restore from Local Backup

```bash
# Stop the application first
docker-compose down

# Restore database
pg_restore \
    --host=localhost \
    --port=5432 \
    --username=shiftsync_user \
    --dbname=shiftsync \
    --clean \
    --if-exists \
    --verbose \
    /var/backups/shiftsync/shiftsync_backup_20240115_020000.sql.gz

# Restart application
docker-compose up -d
```

### Restore from Azure Blob

```bash
# Download backup
az storage blob download \
    --container-name shiftsync-backups \
    --name shiftsync_backup_20240115_020000.sql.gz \
    --file /tmp/restore.sql.gz

# Restore
pg_restore \
    --host=shiftsync-db.postgres.database.azure.com \
    --port=5432 \
    --username=shiftsync_admin \
    --dbname=shiftsync \
    --clean \
    --if-exists \
    /tmp/restore.sql.gz
```

## Disaster Recovery Plan

### RTO/RPO Targets

| Scenario | RTO (Recovery Time) | RPO (Data Loss) |
|----------|---------------------|-----------------|
| Single server failure | 30 minutes | 0-1 hour |
| Region outage | 4 hours | 0-24 hours |
| Data corruption | 2 hours | 0-1 hour |

### Recovery Steps

#### 1. Database Corruption
1. Stop application
2. Identify last good backup
3. Restore from backup
4. Verify data integrity
5. Restart application

#### 2. Complete Server Failure
1. Deploy new container instance
2. Restore database from Azure backup
3. Update DNS/load balancer
4. Verify functionality

#### 3. Regional Disaster
1. Activate geo-redundant backup
2. Deploy to secondary region
3. Update frontend API endpoint
4. Notify users of any data loss

## Verification

### Monthly Backup Test

```bash
# 1. Create test database
createdb shiftsync_test

# 2. Restore latest backup
pg_restore \
    --dbname=shiftsync_test \
    /var/backups/shiftsync/latest_backup.sql.gz

# 3. Verify record counts
psql -d shiftsync_test -c "SELECT COUNT(*) FROM upload_analytics;"

# 4. Compare with production
psql -d shiftsync -c "SELECT COUNT(*) FROM upload_analytics;"

# 5. Cleanup
dropdb shiftsync_test
```

### Backup Monitoring

Set up alerts for:
- Backup job failures
- Backup size anomalies
- Missing daily backups

## Security Considerations

1. **Encryption**: Backups are encrypted at rest in Azure
2. **Access Control**: Only admin users can access backups
3. **Retention**: Follow GDPR retention requirements
4. **Audit**: Log all restore operations

## Contact

For backup/restore emergencies:
- On-call: [your-oncall-system]
- Escalation: [your-email]
