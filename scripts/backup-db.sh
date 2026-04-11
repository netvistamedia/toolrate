#!/bin/bash
# Daily PostgreSQL backup with 7-day retention
set -euo pipefail

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="nemoflow_${TIMESTAMP}.sql.gz"
RETAIN_DAYS=7

echo "[$(date -Iseconds)] Starting backup..."

pg_dump -h postgres -U nemo nemoflow | gzip > "${BACKUP_DIR}/${FILENAME}"

echo "[$(date -Iseconds)] Backup created: ${FILENAME} ($(du -h "${BACKUP_DIR}/${FILENAME}" | cut -f1))"

# Remove backups older than retention period
find "${BACKUP_DIR}" -name "nemoflow_*.sql.gz" -mtime +${RETAIN_DAYS} -delete

echo "[$(date -Iseconds)] Cleanup complete. Current backups:"
ls -lh "${BACKUP_DIR}"/nemoflow_*.sql.gz 2>/dev/null || echo "  (none)"
