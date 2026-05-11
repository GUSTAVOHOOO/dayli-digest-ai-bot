#!/bin/bash
set -e

BACKUP_DIR="data/backups"
DB_FILE="data/articles.db"
KEEP_BACKUPS=7

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/articles_${TIMESTAMP}.db"

echo "💾 Backing up database..."

if [ -f "$DB_FILE" ]; then
    cp "$DB_FILE" "$BACKUP_FILE"
    gzip "$BACKUP_FILE"
    echo "✅ Backup saved: ${BACKUP_FILE}.gz"

    # Clean up old backups
    ls -t $BACKUP_DIR/articles_*.db.gz | tail -n +$((KEEP_BACKUPS+1)) | xargs -r rm

    echo "🧹 Cleanup complete. Keeping last $KEEP_BACKUPS backups."
else
    echo "⚠️  Database file not found at $DB_FILE"
fi
