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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS github_repo_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                stars INTEGER DEFAULT 0,
                forks INTEGER DEFAULT 0,
                open_issues INTEGER DEFAULT 0,
                watchers INTEGER DEFAULT 0,
                contributors INTEGER DEFAULT 0,
                releases INTEGER DEFAULT 0,
                captured_at TEXT NOT NULL,
                created_at TEXT,
                pushed_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_repo_snapshot_name_time ON github_repo_snapshots(full_name, captured_at)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS source_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url TEXT NOT NULL UNIQUE,
                source_type TEXT NOT NULL,
                entity TEXT NOT NULL,
                reason TEXT,
                origin_url TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_source_suggestions_status ON source_suggestions(status)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                first_seen_at TEXT DEFAULT (datetime('now')),
                last_seen_at TEXT DEFAULT (datetime('now')),
                UNIQUE(normalized_name, entity_type)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_entity_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                target_key TEXT NOT NULL,
                target_type TEXT NOT NULL,
                context_url TEXT,
                weight REAL DEFAULT 1.0,
                first_seen_at TEXT DEFAULT (datetime('now')),
                last_seen_at TEXT DEFAULT (datetime('now')),
                UNIQUE(source_entity_id, relation_type, target_key, target_type)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_relations_target ON knowledge_relations(target_key, target_type)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS platform_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT NOT NULL,
                metric_name TEXT,
                count REAL DEFAULT 1,
                source TEXT,
                reason TEXT,
                duration_ms REAL,
                metadata_json TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
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


def get_latest_repo_snapshot(full_name: str) -> Optional[dict]:
    """Returns the latest GitHub repo snapshot for velocity comparison."""
    init_db()
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT *
            FROM github_repo_snapshots
            WHERE full_name = ?
            ORDER BY captured_at DESC
            LIMIT 1
        """, (full_name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def save_repo_snapshot(snapshot) -> int:
    """Persists a GitHub repo snapshot and returns its row id."""
    init_db()
    data = snapshot.to_dict() if hasattr(snapshot, "to_dict") else dict(snapshot)
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO github_repo_snapshots (
                full_name, stars, forks, open_issues, watchers, contributors,
                releases, captured_at, created_at, pushed_at
            )
            VALUES (
                :full_name, :stars, :forks, :open_issues, :watchers, :contributors,
                :releases, :captured_at, :created_at, :pushed_at
            )
        """, data)
        conn.commit()
        return int(cursor.lastrowid)


def save_source_suggestion(suggestion: dict) -> dict:
    """Persists a pending source suggestion without auto-activating it."""
    init_db()
    data = {
        "source_url": suggestion.get("source_url"),
        "source_type": suggestion.get("source_type"),
        "entity": suggestion.get("entity"),
        "reason": suggestion.get("reason", ""),
        "origin_url": suggestion.get("origin_url", ""),
        "status": suggestion.get("status", "pending"),
    }
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO source_suggestions (
                source_url, source_type, entity, reason, origin_url, status
            )
            VALUES (
                :source_url, :source_type, :entity, :reason, :origin_url, :status
            )
            ON CONFLICT(source_url) DO UPDATE SET
                reason = COALESCE(NULLIF(excluded.reason, ''), source_suggestions.reason),
                origin_url = COALESCE(NULLIF(excluded.origin_url, ''), source_suggestions.origin_url)
            RETURNING *
        """, data)
        row = cursor.fetchone()
        conn.commit()
        return dict(row) if row else data


def get_source_suggestion(source_url: str) -> Optional[dict]:
    init_db()
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM source_suggestions WHERE source_url = ?", (source_url,))
        row = cursor.fetchone()
        return dict(row) if row else None


def upsert_knowledge_entity(entity: dict) -> int:
    """Creates or touches an entity in the local knowledge graph."""
    init_db()
    name = str(entity.get("name") or entity.get("normalized_name") or "").strip()
    normalized_name = str(entity.get("normalized_name") or name).strip().lower()
    entity_type = str(entity.get("type") or entity.get("entity_type") or "concept").strip()
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO knowledge_entities (name, normalized_name, entity_type)
            VALUES (?, ?, ?)
            ON CONFLICT(normalized_name, entity_type) DO UPDATE SET
                name = excluded.name,
                last_seen_at = datetime('now')
            RETURNING id
        """, (name, normalized_name, entity_type))
        row = cursor.fetchone()
        conn.commit()
        return int(row["id"])


def save_knowledge_relation(
    source_entity_id: int,
    relation_type: str,
    target_key: str,
    target_type: str,
    context_url: str = "",
    weight: float = 1.0,
) -> int:
    """Creates or touches a simple graph relation."""
    init_db()
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO knowledge_relations (
                source_entity_id, relation_type, target_key, target_type, context_url, weight
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_entity_id, relation_type, target_key, target_type) DO UPDATE SET
                context_url = COALESCE(NULLIF(excluded.context_url, ''), knowledge_relations.context_url),
                weight = MAX(knowledge_relations.weight, excluded.weight),
                last_seen_at = datetime('now')
            RETURNING id
        """, (source_entity_id, relation_type, target_key, target_type, context_url, weight))
        row = cursor.fetchone()
        conn.commit()
        return int(row["id"])


def get_entity_history(normalized_name: str, entity_type: Optional[str] = None) -> List[dict]:
    """Returns graph relations for a normalized entity name."""
    init_db()
    with get_connection() as conn:
        params = [normalized_name.lower()]
        entity_filter = ""
        if entity_type:
            entity_filter = "AND e.entity_type = ?"
            params.append(entity_type)
        cursor = conn.execute(f"""
            SELECT e.*, r.relation_type, r.target_key, r.target_type, r.context_url, r.weight, r.last_seen_at AS relation_last_seen_at
            FROM knowledge_entities e
            LEFT JOIN knowledge_relations r ON r.source_entity_id = e.id
            WHERE e.normalized_name = ?
            {entity_filter}
            ORDER BY r.last_seen_at DESC
        """, params)
        return [dict(row) for row in cursor.fetchall()]


def get_entities_related_to(target_key: str, target_type: str = "cluster") -> List[dict]:
    """Returns entities related to a topic or cluster key."""
    init_db()
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT e.*, r.relation_type, r.target_key, r.target_type, r.context_url, r.weight
            FROM knowledge_relations r
            JOIN knowledge_entities e ON e.id = r.source_entity_id
            WHERE r.target_key = ? AND r.target_type = ?
            ORDER BY r.weight DESC, r.last_seen_at DESC
        """, (target_key, target_type))
        return [dict(row) for row in cursor.fetchall()]


def save_metric_event(event: dict) -> int:
    """Persists a cheap local metric event."""
    init_db()
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO platform_metrics (
                event_name, metric_name, count, source, reason, duration_ms, metadata_json
            )
            VALUES (
                :event_name, :metric_name, :count, :source, :reason, :duration_ms, :metadata_json
            )
        """, event)
        conn.commit()
        return int(cursor.lastrowid)
