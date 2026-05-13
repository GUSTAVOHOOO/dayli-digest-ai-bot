import sqlite3
import os
from contextlib import contextmanager
from typing import Optional, List
from src.models.article import Article
from src.utils.config_loader import load_env

# Ensure env is loaded
load_env()
DB_PATH = os.getenv('SQLITE_DB_PATH', 'data/articles.db')

@contextmanager
def get_connection():
    """Provides a thread-safe connection to the SQLite database."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        yield conn
    finally:
        conn.close()

def init_db() -> None:
    """Initializes the database schema and indexes."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT,
                source TEXT NOT NULL,
                date_published TEXT,
                date_processed TEXT DEFAULT (datetime('now')),
                summary TEXT,
                score REAL DEFAULT 0,
                md5_hash TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'processed',
                analysis_json TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON processed_articles(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_md5 ON processed_articles(md5_hash)")
        conn.commit()

def is_article_processed(md5_hash: str) -> bool:
    """Checks if an article has already been processed based on its MD5 hash."""
    init_db()
    with get_connection() as conn:
        cursor = conn.execute("SELECT 1 FROM processed_articles WHERE md5_hash = ?", (md5_hash,))
        return cursor.fetchone() is not None

def save_article(article: Article) -> int:
    """Saves or updates an article in the database."""
    init_db()
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO processed_articles (url, title, source, date_published, summary, score, md5_hash, status, analysis_json)
            VALUES (:url, :title, :source, :date_published, :summary, :score, :md5_hash, :status, :analysis_json)
            ON CONFLICT(md5_hash) DO UPDATE SET
                summary = excluded.summary,
                score = excluded.score,
                status = excluded.status,
                analysis_json = excluded.analysis_json
            RETURNING id
        """, article.to_dict())
        row = cursor.fetchone()
        conn.commit()
        return row[0] if row else 0

def get_articles_by_date(date_str: str, min_score: float = 0.0) -> List[Article]:
    """Retrieves processed articles for a specific date (YYYY-MM-DD) with status 'processed' and valid score/summary."""
    init_db()
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT * FROM processed_articles
            WHERE date_processed LIKE ? 
            AND status = 'processed'
            AND score >= ?
            AND summary IS NOT NULL
            AND summary != ''
        """, (f"{date_str}%", min_score))
        return [Article.from_dict(dict(row)) for row in cursor.fetchall()]
def get_last_digest_date() -> Optional[str]:
    """Retrieves the date of the last processed article."""
    init_db()
    with get_connection() as conn:
        cursor = conn.execute("SELECT MAX(date_processed) FROM processed_articles")
        row = cursor.fetchone()
        return row[0] if row and row[0] else None
