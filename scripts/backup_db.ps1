# Database Backup for Windows (PowerShell)

$BACKUP_DIR = "data/backups"
$DB_FILE = "data/articles.db"
$KEEP_BACKUPS = 7

if (!(Test-Path $BACKUP_DIR)) { New-Item -ItemType Directory $BACKUP_DIR }

$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$BACKUP_FILE = "$BACKUP_DIR/articles_$TIMESTAMP.db"

echo "💾 Backing up database..."

if (Test-Path $DB_FILE) {
    Copy-Item $DB_FILE $BACKUP_FILE
    # Use built-in compression if available, otherwise just keep as .db
    # Compress-Archive is for folders, so we'll just keep it simple
    echo "✅ Backup saved: $BACKUP_FILE"

    # Clean up old backups
    $backups = Get-ChildItem "$BACKUP_DIR/articles_*.db" | Sort-Object LastWriteTime -Descending
    if ($backups.Count -gt $KEEP_BACKUPS) {
        $backups | Select-Object -Skip $KEEP_BACKUPS | Remove-Item
        echo "🧹 Cleanup complete. Keeping last $KEEP_BACKUPS backups."
    }
} else {
    echo "⚠️  Database file not found at $DB_FILE"
}
